"""
会话消息存储模块

负责：
1. 消息的持久化存储（MySQL）
2. 会话历史查询
3. 消息的增删改查

设计原则：
- 支持按会话ID分组
- 支持分页查询
- 支持消息类型区分（用户消息/Agent响应）
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# 尝试导入SQLAlchemy
try:
    from sqlalchemy import Column, Integer, String, Text, DateTime, Index
    from sqlalchemy.ext.declarative import declarative_base
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Base = None
    logger.warning("SQLAlchemy未安装，消息存储功能不可用")


if SQLALCHEMY_AVAILABLE:
    class Message(Base):
        """
        消息表模型

        存储所有的对话消息，包括用户消息和Agent响应
        """
        __tablename__ = 'chat_messages'

        id = Column(Integer, primary_key=True, autoincrement=True)
        session_id = Column(String(64), nullable=False, index=True, comment='会话ID')
        user_id = Column(String(64), nullable=True, index=True, comment='用户ID')
        role = Column(String(20), nullable=False, comment='角色: user/assistant/system')
        content = Column(Text, nullable=False, comment='消息内容')
        message_type = Column(String(20), default='text', comment='消息类型: text/tool_call/tool_result')
        metadata = Column(Text, nullable=True, comment='额外元数据(JSON)')
        created_at = Column(DateTime, default=datetime.now, comment='创建时间')

        # 创建复合索引
        __table_args__ = (
            Index('idx_session_created', 'session_id', 'created_at'),
        )

        def to_dict(self) -> Dict[str, Any]:
            """转换为字典"""
            return {
                'id': self.id,
                'session_id': self.session_id,
                'user_id': self.user_id,
                'role': self.role,
                'content': self.content,
                'message_type': self.message_type,
                'metadata': self.metadata,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }


class MessageStore:
    """
    消息存储服务

    提供消息的增删改查操作
    """

    def __init__(self, db_manager=None):
        """
        初始化消息存储

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self._initialized = False

    def init_db(self, db_manager):
        """
        初始化数据库连接

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager
        self._ensure_tables()
        self._initialized = True
        logger.info("✅ 消息存储初始化完成")

    def _ensure_tables(self):
        """确保表已创建"""
        if self.db and hasattr(self.db, 'Base') and Base:
            # 将 Message 模型注册到 Base
            Message.__table__.metadata = self.db.Base.metadata
            self.db.Base.metadata.create_all(self.db.engine, tables=[Message.__table__])
            logger.info("✅ 消息表已创建/验证")

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        message_type: str = 'text',
        metadata: Optional[str] = None
    ) -> Optional[int]:
        """
        保存消息

        Args:
            session_id: 会话ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            user_id: 用户ID（可选）
            message_type: 消息类型
            metadata: 额外元数据

        Returns:
            消息ID，失败返回None
        """
        if not self.db:
            logger.warning("数据库未初始化，消息未保存")
            return None

        try:
            query = """
                INSERT INTO chat_messages
                (session_id, user_id, role, content, message_type, metadata, created_at)
                VALUES (:session_id, :user_id, :role, :content, :message_type, :metadata, NOW())
            """
            params = {
                'session_id': session_id,
                'user_id': user_id,
                'role': role,
                'content': content,
                'message_type': message_type,
                'metadata': metadata
            }
            self.db.execute_update(query, params)
            logger.debug(f"消息已保存: session={session_id}, role={role}")
            return True
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return None

    def get_session_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史消息

        Args:
            session_id: 会话ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            消息列表
        """
        if not self.db:
            logger.warning("数据库未初始化，无法获取历史")
            return []

        try:
            query = """
                SELECT id, session_id, user_id, role, content, message_type, metadata, created_at
                FROM chat_messages
                WHERE session_id = :session_id
                ORDER BY created_at ASC
                LIMIT :limit OFFSET :offset
            """
            params = {
                'session_id': session_id,
                'limit': limit,
                'offset': offset
            }
            results = self.db.execute_query(query, params)
            logger.debug(f"获取历史消息: session={session_id}, count={len(results)}")
            return results
        except Exception as e:
            logger.error(f"获取历史消息失败: {e}")
            return []

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话消息

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        if not self.db:
            return False

        try:
            query = "DELETE FROM chat_messages WHERE session_id = :session_id"
            self.db.execute_update(query, {'session_id': session_id})
            logger.info(f"会话已清除: {session_id}")
            return True
        except Exception as e:
            logger.error(f"清除会话失败: {e}")
            return False

    def get_recent_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        获取用户最近的会话列表

        Args:
            user_id: 用户ID
            limit: 返回数量

        Returns:
            会话列表
        """
        if not self.db:
            return []

        try:
            query = """
                SELECT session_id, MAX(created_at) as last_message_time
                FROM chat_messages
                WHERE user_id = :user_id
                GROUP BY session_id
                ORDER BY last_message_time DESC
                LIMIT :limit
            """
            return self.db.execute_query(query, {'user_id': user_id, 'limit': limit})
        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return []


# 全局单例
_message_store: Optional[MessageStore] = None


def get_message_store() -> MessageStore:
    """获取消息存储单例"""
    global _message_store
    if _message_store is None:
        _message_store = MessageStore()
    return _message_store


def init_message_store(db_manager) -> MessageStore:
    """初始化消息存储"""
    global _message_store
    _message_store = MessageStore(db_manager)
    return _message_store
