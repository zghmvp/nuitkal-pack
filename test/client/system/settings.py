# core
import os
from pathlib import Path

from zghmvp.tools.system import autodiscover_apps, load_config

BASE_DIR = Path(__file__).resolve().parent.parent

INSTALLED_APPS = autodiscover_apps("zghmvp", "apps")

config = load_config()["django"]
DATABASES = config["DATABASES"]
CACHES = config["CACHES"]

LANGUAGE_CODE = "zh-Hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = False

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
