from nuitkal_pack import UpdaterConfig, UpdaterManager

# 创建更新器配置
config = UpdaterConfig(
    check_api_url="http://ps.19970128.xyz/api/client_update/apps/e8d0ad0cf6e84c73b0918b18c0c98a95/active/",  # 服务端地址
    # check_api_url="http://127.0.0.1:8000/api/client_update/apps/bd1bf1b1fb68477cb18338348302046c/active/",  # 服务端地址
)


# def progress_callback(downloaded: int, total: int) -> None:
#     if total > 0:
#         percent = (downloaded / total) * 100
#         print(f"下载进度: {percent:.1f}% ({downloaded}/{total} bytes)")
#     else:
#         print(f"已下载: {downloaded} bytes")


# # 使用统一的进度回调工厂
# config.progress_callback = progress_callback

# 使用上下文管理器确保资源正确释放
with UpdaterManager(config) as updater:
    updater.update_and_run()
