# zghmvp-client-update

一个 Django 应用,用于管理客户端版本更新和自动分发。

## 功能特性

### 服务端功能
- 版本管理与存储
- 更新包上传(ZIP格式)
- SHA256 文件完整性校验
- 语义化版本号支持
- 版本激活/停用控制
- RESTful API 接口
- Django Admin 后台管理

### 客户端功能
- 打包客户端为 ZIP 文件，支持只打包有更新的文件（通过与服务器对比文件哈希实现）
- 自动版本检查
- 更新包下载(带进度回调)
- 文件完整性校验(SHA256)
- 自动备份和回滚机制
- 语义化版本比较
- 完整的日志系统
- 自动重试机制(网络异常)
- 异常安全处理
- 支持多种主程序类型(Python/Shell/Batch/可执行文件)

## 依赖要求

- Python >= 3.8
- Django >= 4.2
- Django REST Framework >= 3.14
- 其他依赖见 [setup.py](setup.py)

## 安装

### 1. 安装
```
pip install git+https://github.com/zghmvp/nuitkal_pack_server.git
```

或克隆本项目后进入根目录执行

```bash
pip install .
```

### 2. 服务端配置

#### 2.1 添加到 INSTALLED_APPS

在 Django 项目的 `settings.py` 中添加:

```python
INSTALLED_APPS = [
    ...
    "rest_framework",
    "nuitkal_pack_server",
]
```

#### 2.2 配置媒体文件路径

确保 `settings.py` 中配置了媒体文件路径:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

#### 2.3 添加 URL 路由

在 Django 项目的 `urls.py` 中添加:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
    path("api/nuitkal_pack/", include("nuitkal_pack_server.urls")),
]

# 开发环境下需要添加媒体文件路由
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

#### 2.4 执行数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

#### 2.5 创建超级用户(可选)

如果需要使用 Django Admin 后台管理版本:

```bash
python manage.py createsuperuser
```

## API 接口说明

### 1. 检查最新版本

```http
GET /api/nuitkal_pack/check/
```

### 2. 获取所有版本列表

```http
GET /api/nuitkal_pack/versions/
```

### 3. 上传新版本

```http
POST /api/nuitkal_pack/upload/
Content-Type: multipart/form-data
```

**请求参数:**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 版本号(如 1.0.1) |
| file | file | 是 | ZIP 格式的更新包文件 |
| changelog | string | 否 | 更新日志说明 |
| is_active | boolean | 否 | 是否设为激活版本,默认 true |

**响应示例:**

```json
{
  "message": "版本上传成功",
  "version": "1.0.1",
  "download_url": "http://localhost:8000/media/nuitkal_packs/2025/01/update_1.0.1.zip",
  "file_hash": "a1b2c3d4e5f6...",
  "file_size": 1048576,
  "is_active": true
}
```

### 4. 设置激活版本

```http
POST /api/nuitkal_pack/set_active/{version}/
```

**响应示例:**

```json
{
  "message": "版本 1.0.1 已设为激活版本",
  "version": "1.0.1"
}
```

## 客户端使用

### 基本使用

```python
from pathlib import Path
from nuitkal_pack import ClientUpdater, UpdaterConfig


def progress_callback(downloaded: int, total: int) -> None:
    """下载进度回调函数"""
    if total > 0:
        percent = (downloaded / total) * 100
        print(f"下载进度: {percent:.1f}% ({downloaded}/{total} bytes)")
    else:
        print(f"已下载: {downloaded} bytes")


def main():
    """启动器主函数"""
    # 创建更新器配置
    config = UpdaterConfig(
        check_api_url="http://localhost:8000/api/nuitkal_pack/check/",  # 服务端检查版本接口
        client_dir=Path("client").resolve(),  # 客户端程序目录
        main_script="main.py",  # 主程序入口文件
    )

    # 设置进度回调
    config.progress_callback = progress_callback

    # 使用上下文管理器确保资源正确释放
    with ClientUpdater(config) as updater:
        # 执行更新并启动主程序
        updater.update_and_run()


if __name__ == "__main__":
    main()
```

### 配置参数说明

[UpdaterConfig](nuitkal_pack/client.py#L120) 主要配置参数:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| check_api_url | str | 必填 | 服务端版本检查接口地址 |
| client_dir | Path | cwd()/client | 客户端程序目录 |
| main_script | str | main.py | 主程序入口文件名(支持 .py/.sh/.bat/.exe) |
| version_file | str | local_version.json | 本地版本信息存储文件 |
| timeout | float | 30.0 | 网络请求超时时间(秒) |
| chunk_size | int | 8192 | 下载分块大小(字节) |
| verify_ssl | bool | False | 是否验证 SSL 证书 |
| progress_callback | Callable | None | 下载进度回调函数(downloaded, total) |

### 支持的主程序类型

客户端更新器支持以下主程序类型:

- **Python 脚本** (`.py`): 使用 Python 解释器运行
- **Shell 脚本** (`.sh`): 使用 bash 运行
- **Batch 脚本** (`.bat`, `.cmd`): Windows 批处理
- **可执行文件** (`.exe` 或无后缀): 直接运行

### 更新流程说明

1. **版本检查**: 对比本地版本与服务端最新版本
2. **下载更新包**: 流式下载到内存,支持进度回调
3. **哈希校验**: SHA256 验证文件完整性
4. **备份当前版本**: 备份到 `.backup` 目录(排除缓存文件)
5. **解压更新包**: 解压到客户端目录
6. **更新版本记录**: 写入本地版本文件
7. **启动主程序**: 根据文件类型自动选择启动方式

**错误处理**: 如果更新过程失败,会自动从备份恢复,确保程序可用性。

## 使用 Django Admin 管理版本

访问 `/admin/` 登录后台,可以:

- 查看所有已上传的版本
- 上传新的更新包
- 编辑版本信息(更新日志等)
- 设置激活版本
- 删除旧版本

## 注意事项

1. **文件格式**: 更新包必须是 ZIP 格式
2. **版本号**: 建议使用语义化版本号(如 1.0.1, 2.0.0)
3. **主程序**: 确保 `main_script` 配置正确,否则客户端无法启动
4. **备份目录**: 更新时会创建 `.backup` 备份目录,请勿手动删除
5. **网络重试**: 客户端内置重试机制
6. **媒体文件**: 生产环境需正确配置 MEDIA_URL 和 MEDIA_ROOT
