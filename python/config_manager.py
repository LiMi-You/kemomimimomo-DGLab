import yaml
from pathlib import Path

class ConfigManager:
    """
    用于加载并提供对配置文件的访问。
    在初始化时读取配置文件，并将配置存储在内存中。
    """
    
    def __init__(self, config_path='config.yaml'):
        """
        初始化ConfigManager实例，并加载配置文件。
        
        :param config_path: 配置文件路径，默认为'config.yaml'
        """
        self._config_path = Path(config_path)
        self._config_data = self._load_config()
    
    def _load_config(self):
        """
        内部方法，用于从YAML文件加载配置。
        
        :return: 包含配置项的字典
        """
        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件 {self._config_path} 不存在")
        
        with self._config_path.open('r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}
    
    def reload(self):
        """重新加载配置文件，覆盖当前内存中的配置"""
        self._config_data = self._load_config()

    def __getattr__(self, name):
        """
        允许以点符号访问配置项，如 config.host
        
        :param name: 配置项名称
        :return: 配置项的值或None如果该项不存在
        """
        # 注意：这里使用get方法来避免键不存在时抛出异常
        return self._config_data.get(name)

