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

from nuitkal_pack.client import UpdateManager

# 创建更新器配置
update_manager = UpdateManager(
    server_url="http://127.0.0.1:8000/api/v1/nuitkal_pack/",
    app_id="0b034342-e951-4944-af4a-50d428a7e59a",
    local_dir=Path("client"),
)
info = update_manager.check_update()
print(info)
update_manager.run_entry_point(info)
