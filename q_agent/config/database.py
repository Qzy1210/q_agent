"""
数据库管理器 - 管理MySQL数据库连接

数据库管理器负责：
1. 创建和管理数据库连接池
2. 提供数据库操作接口
3. 处理数据库异常
4. 管理事务

学习重点：
1. 理解数据库连接池的作用
2. 掌握SQLAlchemy的使用
3. 学习数据库事务管理
"""

from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

# 数据库相关导入
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker, scoped_session
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.pool import QueuePool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️ 未安装SQLAlchemy，数据库功能不可用")

# 配置日志
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库管理器主类
    
    负责管理MySQL数据库连接，提供统一的数据库操作接口。
    
    属性说明：
        engine: SQLAlchemy引擎
        session_factory: Session工厂
        Base: 模型基类
        
    设计思路：
    - 使用连接池管理连接
    - 提供上下文管理器管理Session
    - 支持事务操作
    - 统一的错误处理
    
    学习要点：
    - 数据库连接池的配置
    - Session管理
    - 事务处理
    - 错误处理
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "q_agent",
        charset: str = "utf8mb4",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 3600
    ):
        """
        初始化数据库管理器
        
        参数：
            host (str): 数据库主机
            port (int): 数据库端口
            user (str): 用户名
            password (str): 密码
            database (str): 数据库名
            charset (str): 字符集
            pool_size (int): 连接池大小
            max_overflow (int): 最大溢出连接数
            pool_recycle (int): 连接回收时间（秒）
        """
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy未安装，无法使用数据库功能")
        
        # 构建连接URL
        self.connection_url = (
            f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
            f"?charset={charset}"
        )
        
        # 创建引擎
        try:
            self.engine = create_engine(
                self.connection_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                echo=False,  # 设置为True可以看到SQL语句
                pool_pre_ping=True  # 自动检测连接是否有效
            )
            
            # 创建Session工厂
            self.session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            
            # 创建模型基类
            self.Base = declarative_base()
            
            # 测试连接
            self._test_connection()
            
            logger.info("✅ 数据库管理器初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 数据库管理器初始化失败: {str(e)}")
            raise
    
    def _test_connection(self):
        """
        测试数据库连接
        
        尝试执行简单查询验证连接是否正常
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("✅ 数据库连接测试成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接测试失败: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self):
        """
        获取数据库Session（上下文管理器）
        
        用途：
        - 自动管理Session生命周期
        - 自动提交/回滚事务
        
        示例：
        with db.get_session() as session:
            session.execute(text("SELECT * FROM users"))
        
        学习要点：
        - 上下文管理器的使用
        - 自动事务管理
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作错误: {str(e)}")
            raise
        finally:
            session.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        参数：
            query (str): SQL查询语句
            params (dict): 参数
            
        返回：
            List[Dict]: 查询结果列表
            
        学习要点：
        - 参数化查询（防止SQL注入）
        - 结果集处理
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                
                # 转换为字典列表
                columns = result.keys()
                rows = []
                for row in result:
                    rows.append(dict(zip(columns, row)))
                
                return rows
                
        except Exception as e:
            logger.error(f"查询执行失败: {str(e)}")
            raise
    
    def execute_update(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        执行更新SQL（INSERT/UPDATE/DELETE）
        
        参数：
            query (str): SQL语句
            params (dict): 参数
            
        返回：
            int: 影响的行数
            
        学习要点：
        - 更新操作
        - 事务管理
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(query), params or {})
                return result.rowcount
                
        except Exception as e:
            logger.error(f"更新执行失败: {str(e)}")
            raise
    
    def create_tables(self):
        """
        创建所有表
        
        根据模型定义创建数据库表
        
        用途：
        - 初始化数据库
        - 创建表结构
        """
        try:
            self.Base.metadata.create_all(self.engine)
            logger.info("✅ 数据库表创建成功")
        except Exception as e:
            logger.error(f"❌ 创建表失败: {str(e)}")
            raise
    
    def drop_tables(self):
        """
        删除所有表
        
        警告：此操作会删除所有数据！
        
        用途：
        - 重置数据库
        - 测试环境清理
        """
        try:
            self.Base.metadata.drop_all(self.engine)
            logger.warning("⚠️ 所有数据库表已删除")
        except Exception as e:
            logger.error(f"❌ 删除表失败: {str(e)}")
            raise
    
    def close(self):
        """
        关闭数据库连接
        
        清理连接池和资源
        
        用途：
        - 应用退出时清理
        - 释放资源
        """
        try:
            self.Session.remove()
            self.engine.dispose()
            logger.info("✅ 数据库连接已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭连接失败: {str(e)}")
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 数据库管理器的描述
        """
        return f"DatabaseManager(url={self.connection_url.split('@')[1] if '@' in self.connection_url else 'N/A'})"


# 使用示例
if __name__ == "__main__":
    """
    数据库管理器使用示例
    
    演示如何使用数据库管理器
    """
    
    print("=" * 60)
    print("数据库管理器使用示例")
    print("=" * 60)
    
    # 创建数据库管理器（需要先创建数据库）
    try:
        db = DatabaseManager(
            host="localhost",
            port=3306,
            user="root",
            password="",
            database="q_agent"
        )
        
        # 测试查询
        print("\n测试查询：")
        result = db.execute_query("SELECT 1 as test")
        print(f"  结果: {result}")
        
        # 执行更新
        print("\n测试更新：")
        # rows = db.execute_update("INSERT INTO test (name) VALUES (:name)", {"name": "test"})
        # print(f"  插入行数: {rows}")
        
        # 关闭连接
        db.close()
        
    except Exception as e:
        print(f"⚠️ 数据库连接失败: {str(e)}")
        print("  请确保：")
        print("  1. MySQL服务已启动")
        print("  2. 数据库已创建")
        print("  3. 用户名密码正确")
        print("  4. 已安装pymysql: pip install pymysql")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
