"""
配置管理器 - 管理项目配置

配置管理器负责：
1. 加载配置文件（YAML/JSON）
2. 管理环境变量
3. 提供配置访问接口
4. 配置验证和默认值

学习重点：
1. 理解配置管理的最佳实践
2. 掌握多种配置源的加载方法
3. 学习环境变量的安全使用
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """
    配置管理器主类
    
    负责管理整个项目的配置，支持：
    - 配置文件加载（YAML/JSON）
    - 环境变量读取
    - 默认值设置
    - 配置验证
    
    属性说明：
        config (Dict): 配置字典
        config_file (str): 配置文件路径
        env_prefix (str): 环境变量前缀
    
    设计思路：
    - 优先级：环境变量 > 配置文件 > 默认值
    - 支持嵌套配置访问
    - 提供类型转换和验证
    
    学习要点：
    - 配置管理模式
    - 环境变量管理
    - 配置验证方法
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        env_prefix: str = "Q_AGENT_"
    ):
        """
        初始化配置管理器
        
        参数：
            config_file (str): 配置文件路径（可选）
            env_prefix (str): 环境变量前缀，默认Q_AGENT_
        """
        self.config: Dict[str, Any] = {}
        self.config_file = config_file
        self.env_prefix = env_prefix
        
        # 加载默认配置
        self._load_defaults()
        
        # 加载配置文件
        if config_file:
            self._load_from_file(config_file)
        
        # 加载环境变量
        self._load_from_env()
        
        print(f"✅ 配置管理器初始化完成")
    
    def _load_defaults(self):
        """
        加载默认配置
        
        默认配置包含：
        - 数据库配置
        - LLM配置
        - Agent配置
        - 日志配置
        """
        self.config = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "",
                "database": "q_agent",
                "charset": "utf8mb4",
                "pool_size": 5,
                "max_overflow": 10
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": "",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            "agent": {
                "max_iterations": 10,
                "timeout": 300,
                "memory_size": 20,
                "context_window": 4000
            },
            "log": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/q_agent.log"
            }
        }
    
    def _load_from_file(self, config_file: str):
        """
        从文件加载配置
        
        参数：
            config_file (str): 配置文件路径
            
        支持格式：
        - JSON (.json)
        - YAML (.yaml/.yml) - 如果安装了PyYAML
        """
        if not os.path.exists(config_file):
            print(f"⚠️ 配置文件不存在: {config_file}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.endswith('.json'):
                    file_config = json.load(f)
                elif config_file.endswith('.yaml') or config_file.endswith('.yml'):
                    try:
                        import yaml
                        file_config = yaml.safe_load(f)
                    except ImportError:
                        print("⚠️ 未安装PyYAML，无法加载YAML配置文件")
                        return
                else:
                    print(f"⚠️ 不支持的配置文件格式: {config_file}")
                    return
            
            # 合并配置（文件配置覆盖默认配置）
            self._merge_config(file_config)
            print(f"✅ 从文件加载配置: {config_file}")
            
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {str(e)}")
    
    def _load_from_env(self):
        """
        从环境变量加载配置
        
        环境变量格式：
        Q_AGENT_DATABASE_HOST=localhost
        Q_AGENT_LLM_API_KEY=sk-xxx
        
        优先级：环境变量 > 配置文件 > 默认值
        """
        # 数据库配置
        self._update_from_env("database.host", "DATABASE_HOST")
        self._update_from_env("database.port", "DATABASE_PORT", int)
        self._update_from_env("database.user", "DATABASE_USER")
        self._update_from_env("database.password", "DATABASE_PASSWORD")
        self._update_from_env("database.database", "DATABASE_NAME")
        
        # LLM配置
        self._update_from_env("llm.api_key", "LLM_API_KEY")
        self._update_from_env("llm.model", "LLM_MODEL")
        self._update_from_env("llm.temperature", "LLM_TEMPERATURE", float)
        
        # Agent配置
        self._update_from_env("agent.max_iterations", "AGENT_MAX_ITERATIONS", int)
        self._update_from_env("agent.timeout", "AGENT_TIMEOUT", int)
    
    def _update_from_env(
        self,
        config_key: str,
        env_key: str,
        value_type: type = str
    ):
        """
        从环境变量更新配置
        
        参数：
            config_key (str): 配置键（支持点号分隔）
            env_key (str): 环境变量名（会自动加前缀）
            value_type (type): 值类型
        """
        full_env_key = f"{self.env_prefix}{env_key}"
        env_value = os.getenv(full_env_key)
        
        if env_value:
            try:
                # 类型转换
                if value_type == bool:
                    env_value = env_value.lower() in ['true', '1', 'yes']
                else:
                    env_value = value_type(env_value)
                
                # 更新配置
                keys = config_key.split('.')
                config = self.config
                for key in keys[:-1]:
                    config = config.setdefault(key, {})
                config[keys[-1]] = env_value
                
            except (ValueError, TypeError) as e:
                print(f"⚠️ 环境变量 {full_env_key} 类型转换失败: {str(e)}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """
        合并配置
        
        参数：
            new_config (Dict): 新配置
            
        合并策略：
        - 深度合并（递归）
        - 新配置覆盖旧配置
        """
        def deep_merge(base: dict, update: dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value
        
        deep_merge(self.config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        参数：
            key (str): 配置键（支持点号分隔）
            default (Any): 默认值
            
        返回：
            Any: 配置值
            
        示例：
        config.get("database.host")
        config.get("llm.api_key")
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        参数：
            key (str): 配置键（支持点号分隔）
            value (Any): 配置值
            
        用途：
        - 动态修改配置
        - 运行时配置更新
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        
        config[keys[-1]] = value
    
    def save_to_file(self, file_path: str):
        """
        保存配置到文件
        
        参数：
            file_path (str): 文件路径
            
        用途：
        - 导出配置
        - 配置持久化
        """
        try:
            # 确保目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
                elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    try:
                        import yaml
                        yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                    except ImportError:
                        print("⚠️ 未安装PyYAML，无法保存为YAML格式")
                        return
            
            print(f"✅ 配置已保存到: {file_path}")
            
        except Exception as e:
            print(f"⚠️ 保存配置失败: {str(e)}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        返回：
            Dict: 完整的配置字典
            
        用途：
        - 查看所有配置
        - 调试配置问题
        """
        return self.config.copy()
    
    def __repr__(self) -> str:
        """
        字符串表示
        
        返回：
            str: 配置的简短描述
        """
        return f"Config(keys={len(self.config)}, source={self.config_file or 'default'})"


# 使用示例
if __name__ == "__main__":
    """
    配置管理器使用示例
    
    演示如何使用配置管理器
    """
    
    print("=" * 60)
    print("配置管理器使用示例")
    print("=" * 60)
    
    # 创建配置管理器
    config = Config()
    
    # 查看配置
    print("\n数据库配置：")
    print(f"  Host: {config.get('database.host')}")
    print(f"  Port: {config.get('database.port')}")
    print(f"  Database: {config.get('database.database')}")
    
    print("\nLLM配置：")
    print(f"  Model: {config.get('llm.model')}")
    print(f"  Temperature: {config.get('llm.temperature')}")
    
    # 修改配置
    print("\n修改配置：")
    config.set("agent.max_iterations", 20)
    print(f"  Max Iterations: {config.get('agent.max_iterations')}")
    
    # 保存配置
    print("\n保存配置：")
    config.save_to_file("config_example.json")
    
    print("\n" + "=" * 60)
    print("示例执行完成！")
    print("=" * 60)
