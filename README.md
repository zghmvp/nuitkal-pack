# Nuitkal Pack

客户端版本更新与自动分发系统，支持增量更新、Nuitka 编译打包、Django 后端管理。

## 功能特性

- **增量更新** - 基于文件 SHA256 哈希对比，仅下载变更文件，节省带宽
- **全量更新** - 首次接入或版本不存在时自动回退到全量下载
- **版本管理** - Django Admin 后台管理应用、版本、文件
- **Nuitka 编译** - 支持将 Python 源码编译为 `.pyd`/`.so` 二进制文件，保护源码
- **多用户分发** - 按用户维度打包，支持核心文件 + 用户文件分离
- **文件去重** - 相同内容文件共享存储，减少服务器空间占用
- **双模式上传** - 支持 ZIP 整包上传和客户端解压逐文件上传

## 项目结构

```
nuitkal-pack/
├── nuitkal_pack/              # 客户端 SDK
│   ├── client.py              # UpdateManager / UploadManager
│   ├── config.py              # 本地版本配置管理
│   └── packager.py            # PythonPackager (Nuitka 编译打包)
├── nuitkal_pack_server/       # Django 服务端 (可复用 App)
│   ├── models.py              # App / AppVersion / VersionFile
│   ├── views.py               # REST API ViewSet
│   ├── serializers.py         # DRF 序列化器
│   ├── admin.py               # Django Admin 配置
│   ├── urls.py                # API 路由
│   └── tools/                 # 工具模块
│       ├── hash_utils.py      # 哈希计算
│       ├── version_service.py # 版本业务逻辑
│       └── types.py           # 类型定义
├── test/                      # 测试与示例
│   ├── server/                # 测试用 Django 项目
│   └── test-client.py         # 客户端测试脚本
├── setup.py
├── requirements.txt
└── ruff.toml
```

## 快速开始

### 环境要求

- Python >= 3.8
- Django >= 4.2 (服务端)
- Nuitka >= 2.8.9 (可选，编译打包时需要)

### 安装

```bash
# 安装服务端依赖
pip install nuitkal-pack[server]

# 安装客户端依赖
pip install nuitkal-pack[client]

# 安装全部依赖
pip install nuitkal-pack[all]

# 开发环境安装
git clone <repo-url>
cd nuitkal-pack
pip install -r requirements.txt
```

### 服务端部署

#### 1. 将 `nuitkal_pack_server` 添加到 Django 项目

```python
# settings.py
INSTALLED_APPS = [
    ...
    "rest_framework",
    "nuitkal_pack_server",
]

# 配置媒体文件存储
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
```

#### 2. 配置 URL 路由

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("api/v1/nuitkal_pack/", include("nuitkal_pack_server.urls")),
]
```

#### 3. 执行数据库迁移

```bash
python manage.py migrate
```

#### 4. 启动服务

```bash
python manage.py runserver 8000
```

访问 `http://localhost:8000/admin/` 进入管理后台创建应用和上传版本。

### 客户端使用

#### 检查并执行更新

```python
from pathlib import Path
from nuitkal_pack import UpdateManager

manager = UpdateManager(
    server_url="http://localhost:8000/api/v1/nuitkal_pack/",
    app_id="<your-app-uuid>",
    local_dir=Path("./app"),
)

# 检查更新并自动下载
manager.check_and_update(
    run_entry_point=True,
    progress_callback=lambda f, d, t: print(f"{f}: {d/t*100:.1f}%"),
)
```

#### 上传新版本 (ZIP 整包)

```python
from pathlib import Path
from nuitkal_pack import UploadManager

uploader = UploadManager(
    server_url="http://localhost:8000/api/v1/nuitkal_pack/",
    app_id="<your-app-uuid>",
)

result = uploader.upload_zip(
    version="1.0.0",
    entry_point="main.py",
    changelog="首次发布",
    is_active=True,
    file=Path("release.zip"),
)
print(f"上传结果: {result.success} - {result.message}")
```

#### 上传新版本 (解压后逐文件上传)

```python
result = uploader.upload_zip(
    version="1.1.0",
    entry_point="main.py",
    changelog="修复已知问题",
    is_active=True,
    file=Path("release.zip"),
    extract_and_upload=True,
)
```

### Nuitka 编译打包

```python
from pathlib import Path
from nuitkal_pack import PythonPackager

packager = PythonPackager(
    source_dir=Path("./my_app"),
    enable_cache=True,
)

# 编译 Python 文件
packager.compile(
    rglob_pattern=["**/*.py"],
    static_files=["**/*.json", "**/*.html", "**/*.css"],
    exclude_files=["tests/**"],
    nuitka_options=["--assume-yes-for-downloads"],
)

# 生成 ZIP 包 (按用户)
zip_files = packager.to_zip()
for user_name, zip_io in zip_files.items():
    with open(f"release_{user_name}.zip", "wb") as f:
        f.write(zip_io.read())
```

#### 源码标签控制

在 Python 文件首行添加标签控制编译行为：

```python
# [core]          - 核心文件，所有用户共享，默认源码模式
# [core-pyd]      - 核心文件，Nuitka 编译为 .pyd/.so
# [core-source]   - 核心文件，保留源码
# [user-admin]    - 仅 admin 用户可见
# [user-vip-pyd]  - 仅 vip 用户可见，编译为二进制
```

## API 接口

所有接口基础路径: `/api/v1/nuitkal_pack/`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `apps/` | 获取可用应用列表 |
| GET | `apps/{id}/` | 获取应用详情 |
| GET | `apps/{id}/list/` | 获取应用所有版本 |
| GET | `apps/{id}/active/` | 获取激活版本 |
| GET | `apps/{id}/check-update/?version=x.x.x` | 检查更新 (支持增量) |
| POST | `apps/{id}/upload-zip/` | ZIP 整包上传 |
| POST | `apps/{id}/upload-file/` | 单文件上传 |
| POST | `apps/{id}/create-version/` | 创建版本记录 |
| POST | `apps/check-files/` | 检查文件是否已存在 |

### 检查更新响应示例

```json
{
  "need_update": true,
  "current_version": "1.0.0",
  "active_version": "1.1.0",
  "entry_point": "main.py",
  "changelog": "新增功能X",
  "add": [
    {"hash": "abc...", "path": "new_module.py", "url": "/media/...", "size": 1024}
  ],
  "keep": [
    {"hash": "def...", "path": "main.py", "url": "/media/...", "size": 2048}
  ],
  "delete": [
    {"hash": "ghi...", "path": "old_module.py", "url": "/media/...", "size": 512}
  ]
}
```

## 开发指南

### 代码规范

项目使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化：

```bash
# 检查
ruff check .

# 自动修复
ruff check --fix .

# 格式化
ruff format .
```

### 运行测试服务

```bash
cd test/server
python manage.py migrate
python manage.py runserver 8080
```

默认管理员账户: `root` / `root`

### 运行客户端测试

```bash
python test/test-client.py
```

## 许可证

MIT License
