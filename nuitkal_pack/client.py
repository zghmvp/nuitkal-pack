"""更新客户端核心实现

提供完整的增量更新功能:
- 检查服务器更新
- 上传新版本 (支持 ZIP 整包和解压后上传两种模式)
- 配置管理
"""

import json
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Optional, TypedDict
from urllib.parse import urljoin, urlparse

import requests

from nuitkal_pack_server.tools import zipfile
from nuitkal_pack_server.tools.hash_utils import calculate_file_hash

from .config import ConfigManager

logger = logging.getLogger(__name__)


class FileInfo(TypedDict):
    hash: str
    path: str
    url: str
    size: int


class UpdateInfo(TypedDict):
    """检查更新返回结果

    Attributes:
        need_update: 是否需要更新
        current_version: 当前本地版本
        active_version: 服务器激活版本
        entry_point: 程序入口文件路径
        changelog: 更新日志
        add: 需要下载的文件列表 {path: file_id}
        keep: 可保留的文件路径列表
        delete: 需要删除的文件路径列表

    """

    need_update: bool
    current_version: Optional[str]
    active_version: str
    entry_point: str
    changelog: str
    add: list[FileInfo]
    keep: list[FileInfo]
    delete: list[FileInfo]


@dataclass
class UploadResult:
    """上传操作结果

    Attributes:
        success: 是否成功
        message: 提示信息
        version: 版本号
        is_active: 是否激活

    """

    success: bool
    message: str
    version: str
    is_active: bool


class UpdateClient:
    """增量更新客户端

    提供完整的版本管理和更新功能:
    - 检查服务器更新
    - 上传新版本 (支持 ZIP 整包和解压后上传两种模式)
    - 配置管理
    """

    def __init__(
        self,
        server_url: str,
        app_id: str,
        local_dir: Path,
        timeout: int = 30,
    ):
        """初始化更新客户端

        Args:
            server_url: 服务器基础 URL (如: http://localhost:8000/api/v1/)
            app_id: 应用唯一标识符 (UUID)
            local_dir: 本地应用目录
            timeout: 网络请求超时时间(秒)

        """
        self.server_url = server_url + ("" if server_url.endswith("/") else "/")
        self.app_id = app_id
        self.local_dir = local_dir.resolve()
        self.timeout = timeout
        self.config_manager = ConfigManager(self.local_dir)

        logger.info(f"初始化 UpdateClient: server_url={self.server_url}, app_id={self.app_id}, local_dir={self.local_dir}")

    def check_update_info(self) -> UpdateInfo:
        """检查服务器是否有新版本

        向服务器查询当前应用的最新版本信息,对比本地版本后返回更新清单。
        支持增量更新(只下载变化的文件)和全量更新。

        Returns:
            UpdateInfo: 更新信息字典,包含:
                - need_update: 是否需要更新 (bool)
                - current_version: 当前本地版本 (Optional[str])
                - active_version: 服务器激活版本 (str)
                - entry_point: 程序入口文件路径 (str)
                - changelog: 更新日志 (str)
                - add: 需要下载的文件 {path: file_id} (dict[str, str])
                - keep: 可保留的文件路径列表 (list[str])
                - delete: 需要删除的文件路径列表 (list[str])

        Raises:
            requests.HTTPError: 网络请求失败
            requests.Timeout: 请求超时
            ValueError: 服务器返回无效数据

        Example:
            >>> client = UpdateClient("http://localhost:8000/api/v1/", "app-uuid", Path("./app"))
            >>> info = client.check_update()
            >>> if info['need_update']:
            ...     print(f"发现新版本: {info['active_version']}")
            ...     print(f"需要下载 {len(info['add'])} 个文件")

        """
        # 1. 获取本地版本
        local_config = self.config_manager.load()
        current_version = local_config.get("version")

        logger.info(f"检查更新: current_version={current_version}, app_id={self.app_id}")

        # 2. 调用服务器检查更新接口
        check_url = urljoin(self.server_url, f"apps/{self.app_id}/check-update/")
        params = {"version": current_version} if current_version else {}

        try:
            response = requests.get(check_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            update_info = response.json()

        except requests.HTTPError as e:
            # 尝试从响应中提取错误信息
            error_msg = "检查更新失败"
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", error_data.get("message", str(e)))
            except Exception:
                error_msg = str(e)
            logger.exception(f"检查更新失败: {error_msg}")
            raise requests.HTTPError(error_msg) from e

        except requests.Timeout as err:
            logger.exception(f"检查更新超时: 超过 {self.timeout} 秒")
            raise requests.Timeout(f"检查更新超时(超过 {self.timeout} 秒)") from err

        return update_info

    def upload_zip(
        self,
        *,
        version: str,
        entry_point: str,
        changelog: str,
        is_active: bool,
        file: Path,
        extract_and_upload: bool = False,
    ) -> UploadResult:
        """上传应用新版本

        支持两种上传模式:
        1. 整包模式: 直接上传 ZIP 文件,服务器端解压处理
        2. 解压模式: 客户端解压 ZIP,逐个上传文件后创建版本

        Args:
            version: 版本号 (如: "1.0.0")
            entry_point: 程序入口文件路径 (如: "main.py")
            changelog: 更新日志说明
            is_active: 是否设为激活版本
            file: ZIP 文件路径
            extract_and_upload: 是否解压后逐文件上传 (默认 False)

        Returns:
            UploadResult: 上传结果,包含 success, message, version, is_active

        Raises:
            FileNotFoundError: ZIP 文件不存在
            zipfile.BadZipFile: 无效的 ZIP 文件
            requests.HTTPError: 上传失败
            requests.Timeout: 请求超时
            ValueError: 服务器返回错误信息

        Example:
            >>> client = UpdateClient("http://localhost:8000/api/v1/", "app-uuid", Path("./app"))
            >>> # 整包上传
            >>> result = client.upload_zip(
            ...     version="1.0.0",
            ...     entry_point="main.py",
            ...     changelog="首次发布",
            ...     is_active=True,
            ...     file=Path("release.zip")
            ... )
            >>> # 解压上传
            >>> result = client.upload_zip(..., extract_and_upload=True)

        """
        # 1. 参数验证
        if not file.exists():
            logger.error(f"ZIP 文件不存在: {file}")
            raise FileNotFoundError(f"ZIP 文件不存在: {file}")

        logger.info(f"开始上传版本: version={version}, entry_point={entry_point}, is_active={is_active}, file={file}, extract_and_upload={extract_and_upload}")

        # 2. 根据模式选择上传方式
        if extract_and_upload:
            return self._upload_extracted_files(
                version=version,
                entry_point=entry_point,
                changelog=changelog,
                is_active=is_active,
                zip_file=file,
            )

        return self._upload_zip_package(
            version=version,
            entry_point=entry_point,
            changelog=changelog,
            is_active=is_active,
            zip_file=file,
        )

    def _upload_zip_package(
        self,
        *,
        version: str,
        entry_point: str,
        changelog: str,
        is_active: bool,
        zip_file: Path,
    ) -> UploadResult:
        """上传 ZIP 整包

        Args:
            version: 版本号
            entry_point: 入口文件
            changelog: 更新日志
            is_active: 是否激活
            zip_file: ZIP 文件路径

        Returns:
            UploadResult: 上传结果

        """
        upload_url = urljoin(self.server_url, f"apps/{self.app_id}/upload-zip/")

        form_data = {
            "version": version,
            "entry_point": entry_point,
            "changelog": changelog,
            "is_active": "true" if is_active else "false",
        }

        files = {"file": zip_file.open("rb")}

        try:
            logger.info(f"上传 ZIP 整包: url={upload_url}, version={version}, file={zip_file.name}")
            response = requests.post(upload_url, data=form_data, files=files, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            logger.info(f"ZIP 整包上传成功: version={result['version']}, is_active={result['is_active']}")

            return UploadResult(
                success=True,
                message=result.get("message", "上传成功"),
                version=result["version"],
                is_active=result["is_active"],
            )

        except requests.HTTPError as e:
            error_msg = self._extract_error_message(e, "ZIP 包上传失败")
            logger.exception(f"ZIP 包上传失败: {error_msg}")
            raise requests.HTTPError(error_msg) from e

    def _upload_extracted_files(
        self,
        *,
        version: str,
        entry_point: str,
        changelog: str,
        is_active: bool,
        zip_file: Path,
    ) -> UploadResult:
        """解压 ZIP 并逐个上传文件

        Args:
            version: 版本号
            entry_point: 入口文件
            changelog: 更新日志
            is_active: 是否激活
            zip_file: ZIP 文件路径

        Returns:
            UploadResult: 上传结果

        """
        # 1. 解压 ZIP 并构建文件清单
        zip_obj = zipfile.ZipFile(zip_file)
        file_manifest: dict[str, str] = {}
        upload_url = urljoin(self.server_url, f"apps/{self.app_id}/upload-file/")

        logger.info(f"开始解压上传: zip_file={zip_file.name}, total_files={len(zip_obj.namelist())}")

        for file_path in zip_obj.namelist():
            # 2. 上传单个文件
            file_name = Path(file_path).name
            file_content = BytesIO(zip_obj.read(file_path))
            files = {"file": (file_name, file_content)}

            try:
                logger.info(f"上传文件: {file_path}")
                response = requests.post(upload_url, files=files, timeout=self.timeout)
                response.raise_for_status()
                file_id = response.json()["id"]
                file_manifest[Path(file_path).as_posix()] = file_id
                logger.info(f"文件上传成功: {file_path} -> file_id={file_id}")

            except requests.HTTPError as e:
                error_msg = self._extract_error_message(e, f"文件上传失败: {file_path}")
                logger.exception(f"文件上传失败: {file_path}, error={error_msg}")
                raise requests.HTTPError(error_msg) from e

        logger.info(f"所有文件上传完成: count={len(file_manifest)}")

        # 3. 创建版本记录
        create_url = urljoin(self.server_url, f"apps/{self.app_id}/create-version/")
        form_data = {
            "version": version,
            "entry_point": entry_point,
            "changelog": changelog,
            "is_active": "true" if is_active else "false",
            "file_manifest": json.dumps(file_manifest),
        }

        try:
            logger.info(f"创建版本记录: version={version}, files_count={len(file_manifest)}")
            response = requests.post(create_url, data=form_data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()

            logger.info(f"版本创建成功: version={result['version']}, is_active={result['is_active']}")

            return UploadResult(
                success=True,
                message=result.get("message", "上传成功"),
                version=result["version"],
                is_active=result["is_active"],
            )

        except requests.HTTPError as e:
            error_msg = self._extract_error_message(e, "版本创建失败")
            logger.exception(f"版本创建失败: {error_msg}")
            raise requests.HTTPError(error_msg) from e

    def _extract_error_message(self, error: requests.HTTPError, default_msg: str) -> str:
        """从 HTTP 错误中提取错误信息

        Args:
            error: HTTP 错误对象
            default_msg: 默认错误消息

        Returns:
            提取的错误信息

        """
        try:
            error_data = error.response.json()
            return error_data.get("error", error_data.get("message", default_msg))
        except Exception:
            return error.response.text if error.response.text else default_msg

    def check_and_update(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> Optional[UpdateInfo]:
        """检查更新并自动下载新版本文件

        Args:
            progress_callback: 下载进度回调函数,接收参数 (文件名, 已下载字节数, 总字节数)
                              返回 None 表示跳过进度显示

        Returns:
            UpdateInfo: 更新信息字典,如果无需更新则返回 None

        Raises:
            requests.HTTPError: 下载文件失败
            requests.Timeout: 下载超时
            IOError: 文件写入失败

        Example:
            >>> def show_progress(filename, downloaded, total):
            ...     pct = downloaded / total * 100 if total > 0 else 0
            ...     print(f"{filename}: {pct:.1f}%")
            >>> client = UpdateClient(...)
            >>> result = client.check_and_update(progress_callback=show_progress)

        """
        # 1. 检查是否有可用更新
        logger.info("开始检查并执行更新")
        update_info = self.check_update_info()
        if update_info["need_update"]:
            logger.info(f"发现新版本: {update_info['active_version']}, 开始下载更新")
        self.download_update(update_info, progress_callback)

    def _download_file_with_progress(
        self,
        url: str,
        target_path: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """下载单个文件并显示进度

        Args:
            url: 下载 URL
            target_path: 目标保存路径
            progress_callback: 进度回调函数

        Raises:
            requests.HTTPError: 下载失败
            IOError: 文件写入失败

        """
        # 1. 创建目标目录
        target_path.parent.mkdir(parents=True, exist_ok=True)
        file_name = target_path.name

        logger.info(f"开始下载文件: {file_name}, url={url}, target={target_path}")

        # 2. 流式下载文件
        response = requests.get(url, stream=True, timeout=self.timeout)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded_size = 0

        logger.info(f"文件大小: {total_size} bytes")

        # 3. 写入文件并报告进度
        with target_path.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # 过滤掉保持活动的新块
                    file_handle.write(chunk)
                    downloaded_size += len(chunk)

                    # 调用进度回调
                    if progress_callback:
                        progress_callback(file_name, downloaded_size, total_size)

        logger.info(f"文件下载完成: {file_name}, size={downloaded_size} bytes")

    def download_update(
        self,
        update_info: UpdateInfo,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        """根据更新信息下载所有需要更新的文件

        Args:
            update_info: 由 check_update_info() 返回的更新信息
            progress_callback: 下载进度回调函数,接收参数 (文件名, 已下载字节数, 总字节数)

        Raises:
            requests.HTTPError: 下载文件失败
            requests.Timeout: 下载超时
            IOError: 文件写入失败

        Example:
            >>> client = UpdateClient(...)
            >>> info = client.check_update_info()
            >>> if info['need_update']:
            ...     client.download_update(info, progress_callback=lambda f, d, t: print(f"{f}: {d/t*100:.1f}%"))

        """
        # 1. 解析服务器基础 URL
        parsed_url = urlparse(self.server_url)
        if not parsed_url.scheme:
            logger.error("服务器 URL 必须包含协议 (如: http:// 或 https://)")
            raise ValueError("服务器 URL 必须包含协议 (如: http:// 或 https://)")
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        add_files = update_info.get("add", [])
        keep_files = update_info.get("keep", [])

        # 2. 下载需要添加的文件
        for idx, file_info in enumerate(add_files, 1):
            download_url = urljoin(base_url, file_info["url"])
            target_path = self.local_dir / file_info["path"]
            logger.info(f"[{idx}/{len(add_files)}] 下载新增文件: {file_info['path']}")
            # 下载并显示进度
            self._download_file_with_progress(url=download_url, target_path=target_path, progress_callback=progress_callback)

        # 3. 更新本地版本配置
        for file_info in keep_files:
            # 检查文件MD5是否匹配
            local_file_path = self.local_dir / file_info["path"]
            if local_file_path.exists():
                with local_file_path.open("rb") as f:
                    local_md5 = calculate_file_hash(f.read())
                    if local_md5 == file_info["hash"]:
                        continue

                logger.warning(f"文件 {file_info['path']} 已存在但校验失败，需要更新")
            else:
                logger.warning(f"文件 {file_info['path']} 不存在，需要添加")

            # 本地文件与服务器不一致（被本地修改了），或者不存在，需要更新
            download_url = urljoin(base_url, file_info["url"])
            self._download_file_with_progress(url=download_url, target_path=local_file_path, progress_callback=progress_callback)

        self.config_manager.save(
            {
                "version": update_info["active_version"],
                "entry_point": update_info["entry_point"],
            }
        )

        logger.info(f"更新检查已完成 当前版本: {update_info['active_version']}")
