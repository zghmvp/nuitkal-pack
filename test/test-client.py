import os
import sys
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))


from nuitkal_pack.client import UpdateClient

# 创建更新器配置
config = UpdateClient(
    server_url="http://127.0.0.1:8000/api/v1/nuitkal_pack_server/",
    app_id="b3f0f112-f214-4937-99c8-825ff80a4fd8",
    local_dir=Path(),
)

config.upload_zip(version="1.0.3", entry_point="main.py", changelog="", is_active=True, file=Path(r"C:\Users\Administrator\Desktop\新建文件夹\1.0.2.zip"), extract_and_upload=True)
