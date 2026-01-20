import json
from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict


class LocalConfig(TypedDict):
    """本地配置类型"""

    version: Optional[str]
    last_check_time: Optional[str]


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Path):
        """初始化配置管理器

        Args:
            config_dir: 配置文件目录

        """
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / ".update_config.json"

    def load(self) -> LocalConfig:
        """加载本地配置

        Returns:
            本地配置字典

        """
        result: LocalConfig = {
            "version": None,
            "last_check_time": None,
        }
        if not self.config_file.exists():
            return result

        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "version": data.get("version"),
                    "last_check_time": data.get("last_check_time"),
                }
        except (OSError, json.JSONDecodeError):
            return result

    def save(self, config: LocalConfig) -> None:
        """保存本地配置

        Args:
            config: 配置字典

        """
        self.config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "version": config.get("version"),
            "last_check_time": config.get("last_check_time"),
        }
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def update_version(self, version: str) -> None:
        """更新版本号

        Args:
            version: 新版本号

        """
        config = self.load()
        config["version"] = version
        config["last_check_time"] = datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
        self.save(config)
