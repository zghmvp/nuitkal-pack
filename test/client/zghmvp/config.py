# core
from pathlib import Path

import yaml

from system.settings import BASE_DIR


def _validate_config(value: str, field_name: str) -> str:
    """验证配置项是否为空

    Args:
        value: 配置值
        field_name: 配置项名称(用于错误提示)

    Returns:
        验证通过后的配置值

    Raises:
        ValueError: 当配置值为空时抛出异常
    """
    if not value:
        raise ValueError(f"请配置{field_name}")
    return value


with open(BASE_DIR / "config.yml", "r", encoding="utf-8") as file:
    config: dict[str, str] = yaml.safe_load(file)["zghmvp"]

APP_ID: str = config["APP_ID"]

BROWSER_CDP_灯塔: str = config["BROWSER_CDP_灯塔"]
BROWSER_CDP_看板: str = config["BROWSER_CDP_看板"]
BROWSER_CDP_大象: str = config["BROWSER_CDP_大象"]

# 商简称
COMPANY: str = _validate_config(config["COMPANY"], "商简称")

# 商配置 灯塔 > 配送看板 > 商配送监控看板 > 右击 > 新标签页中打开框架 > 根据地址栏把对应值替换
SUPPLIER_ID: str = _validate_config(config["SUPPLIER_ID"], "商ID")
SUPPLIER_NAME: str = _validate_config(config["SUPPLIER_NAME"], "商名称")

# 下载客诉明细的群ID
大象审核群ID: str = _validate_config(config["大象审核群ID"], "大象审核群ID")

# 数据导出目录
FILE_SAVE_DIR: Path = Path(config["FILE_SAVE_DIR"]).resolve()
