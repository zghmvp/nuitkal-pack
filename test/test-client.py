import logging
import sys
from pathlib import Path

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

sys.path.append(str(Path(__file__).parent.parent))

from nuitkal_pack.client import UpdateClient

# 创建更新器配置
config = UpdateClient(
    server_url="http://127.0.0.1:8000/api/v1/nuitkal_pack/",
    app_id="52358670-fdfd-4794-9365-e4e80321fd37",
    local_dir=Path("client"),
)
config.check_and_update()
# config.upload_zip(
#     version="1.0.3", entry_point="main.py", changelog="", is_active=True, file=Path(r"C:\Users\Administrator\Desktop\tuke-new\dist\lianda.zip"), extract_and_upload=True
# )
