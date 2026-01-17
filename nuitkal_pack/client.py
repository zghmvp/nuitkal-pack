"""
客户端自动更新器

支持功能:
- 版本检查
- 更新包下载(带进度回调)
- 文件完整性校验(SHA256)
- 自动备份和回滚
- 语义化版本比较
- 完整的日志系统
- 自动重试机制
- 异常安全处理

第三方库:
- httpx: 现代化的 HTTP 客户端
- tenacity: 强大的重试库
"""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import IO, Callable, Optional
from urllib.parse import urlparse

import httpx
from benedict import benedict
from packaging.version import parse as parse_version
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def setup_logger():
    """配置 logging 日志系统"""
    # 创建日志记录器
    logger = logging.getLogger("zghmvp-updater")
    logger.setLevel(logging.DEBUG)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 控制台输出格式
    console_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# ============================================================================
# 自定义异常类
# ============================================================================


class UpdaterError(Exception):
    """更新器基础异常类"""

    pass


class VersionCheckError(UpdaterError):
    """版本检查失败异常"""

    pass


class DownloadError(UpdaterError):
    """下载失败异常"""

    pass


class VerificationError(UpdaterError):
    """文件验证失败异常"""

    pass


class BackupError(UpdaterError):
    """备份操作失败异常"""

    pass


class RestoreError(UpdaterError):
    """恢复操作失败异常"""

    pass


class ExtractionError(UpdaterError):
    """解压失败异常"""

    pass


class MainScriptError(UpdaterError):
    """主程序脚本错误异常"""

    pass


# ============================================================================
# 配置数据类
# ============================================================================


@dataclass
class UpdaterConfig:
    """更新器配置类"""

    check_api_url: str
    field_entry_point: str = "entry_point"  # 服务端入口点字段名称
    field_version: str = "version"  # 服务端版本字段名称
    field_download_url: str = "file"  # 服务端下载 URL 字段名称
    field_file_hash: str = "file_hash"  # 服务端文件哈希字段名称
    field_changelog: str = "changelog"  # 服务端变更日志字段名称

    client_dir: Path = Path.cwd() / "client"  # 客户端运行目录，解压也是解压到这里
    version_file: str = "local_version.json"  # 本地版本文件名称，用于存储当前客户端版本，一般不用修改
    timeout: float = 30.0  # 请求超时时间，单位秒
    chunk_size: int = 8192  # 下载文件时的 chunk 大小，单位字节
    backup_excludes: tuple = field(
        default_factory=lambda: (
            ".backup",
            "*.pyc",
            "__pycache__",
            ".git",
            "*.zip",
        )
    )  # 备份时需要忽略的文件模式
    verify_ssl: bool = False  # 是否验证 SSL 证书
    progress_callback: Optional[Callable[[int, int], None]] = None  # 下载进度回调函数，参数为 (已下载字节数, 总字节数)

    def __post_init__(self) -> None:
        """初始化后校验配置"""
        if not self.client_dir.exists():
            os.makedirs(self.client_dir)


@dataclass
class VersionInfo:
    """版本信息数据类"""

    entry_point: str
    version: str
    download_url: str
    file_hash: str
    changelog: str = ""


# ============================================================================
# 主更新器类
# ============================================================================


class UpdaterManager:
    """
    客户端自动更新器类

    使用示例:
        config = UpdaterConfig(
            api_check='http://localhost:8000/api/nuitkal_pack/check/',
            client_dir=Path('client')
        )
        updater = UpdaterManager(config)
        updater.update_and_run()
    """

    def __init__(self, config: UpdaterConfig) -> None:
        """
        初始化更新器

        Args:
            config: 更新器配置对象
        """
        self.config = config

        # 配置 loguru 日志
        self.logger = setup_logger()

        # 路径配置
        self.version_file = config.client_dir / config.version_file
        self.backup_dir = config.client_dir / ".backup"

        # httpx 客户端配置
        self._http_client = httpx.Client(timeout=config.timeout, verify=config.verify_ssl, follow_redirects=True)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口,确保关闭 httpx 客户端"""
        self._http_client.close()
        return False

    # -------------------------------------------------------------------------
    # 版本管理方法
    # -------------------------------------------------------------------------

    def get_local_version(self) -> Optional[str]:
        """
        获取本地版本号

        Returns:
            本地版本号,如果不存在则返回 None
        """
        if not self.version_file.exists():
            self.logger.debug("本地版本文件不存在")
            return None

        try:
            with open(self.version_file, "r", encoding="utf-8") as f:
                data = benedict(json.load(f))
                version = data.get(self.config.field_version)
                return version
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"读取本地版本文件失败: {e}")
            return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    )
    def get_active_version(self) -> Optional[VersionInfo]:
        """
        获取服务器最新版本信息

        Returns:
            版本信息对象,如果请求失败则返回 None

        Raises:
            VersionCheckError: 版本检查失败
        """
        try:
            response = self._http_client.get(self.config.check_api_url)
            response.raise_for_status()

            data = benedict(response.json())

            # 检查是否有可用版本
            if not data.get("version"):
                self.logger.warning("服务器暂无可用版本")
                return None

            parsed_url = urlparse(self.config.check_api_url)
            version_info = VersionInfo(
                entry_point=data[self.config.field_entry_point],
                version=data[self.config.field_version],
                download_url="{}://{}{}".format(parsed_url.scheme, parsed_url.netloc, data[self.config.field_download_url]),
                file_hash=data[self.config.field_file_hash],
                changelog=data.get(self.config.field_changelog, ""),
            )
            return version_info

        except httpx.HTTPError as e:
            self.logger.error(f"获取服务器版本信息失败: {e}")
            raise VersionCheckError(f"无法获取远程版本: {e}") from e

        except (KeyError, ValueError) as e:
            self.logger.error(f"解析版本信息失败: {e}")
            raise VersionCheckError(f"版本信息格式错误: {e}") from e

    def compare_versions(self, local: str, remote: str) -> bool:
        """
        比较版本号

        Args:
            local: 本地版本号
            remote: 远程版本号

        Returns:
            True 表示远程版本更新
        """
        try:
            if remote == local:
                self.logger.info("当前已是最新版本，无需更新")
                return False

            elif parse_version(remote) > parse_version(local):
                self.logger.info(f"发现新版本: {local} -> {remote}")

            else:
                self.logger.info(f"发现降级版本：{local} -> {remote}")

            return True

        except Exception as e:
            self.logger.error(f"版本号比较失败: {e}")
            return False

    # -------------------------------------------------------------------------
    # 文件操作方法
    # -------------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, IOError)),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING),
    )
    def download_file(self, url: str) -> tuple[tempfile.SpooledTemporaryFile[bytes], str]:
        """
        下载文件到内存并计算哈希值

        Args:
            url: 下载地址

        Returns:
            (文件对象, SHA256哈希值)

        Raises:
            DownloadError: 下载失败
        """
        try:
            self.logger.info("开始下载更新包...")

            # 创建内存中的临时文件
            temp_file = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024, mode="w+b")
            sha256_hash = hashlib.sha256()

            # 使用 httpx 流式下载
            with self._http_client.stream("GET", url) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                for chunk in response.iter_bytes(chunk_size=self.config.chunk_size):
                    # 写入文件
                    temp_file.write(chunk)

                    # 计算哈希
                    sha256_hash.update(chunk)

                    downloaded += len(chunk)

                    # 调用进度回调
                    if self.config.progress_callback:
                        self.config.progress_callback(downloaded, total_size)

                # 重置文件指针到开始位置
                temp_file.seek(0)

            file_hash = sha256_hash.hexdigest()
            self.logger.info(f"下载完成, SHA256: {file_hash}")

            return temp_file, file_hash

        except httpx.HTTPError as e:
            self.logger.error(f"下载失败: {e}")
            raise DownloadError(f"下载失败: {e}") from e

        except Exception as e:
            self.logger.error(f"下载过程出现错误: {e}")
            raise DownloadError(f"下载时发生意外错误: {e}") from e

    def backup_client(self) -> bool:
        """
        备份当前客户端目录

        Returns:
            备份是否成功

        Raises:
            BackupError: 备份失败
        """
        self.logger.info("正在备份当前客户端...")

        try:
            # 删除旧备份
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
                self.logger.debug("已删除旧备份")

            # 创建新备份
            shutil.copytree(self.config.client_dir, self.backup_dir, ignore=shutil.ignore_patterns(*self.config.backup_excludes), dirs_exist_ok=False)

            self.logger.info(f"备份完成: {self.backup_dir} ✓")
            return True

        except (shutil.Error, IOError) as e:
            self.logger.error(f"✗ 备份失败: {e}")
            raise BackupError(f"备份操作失败: {e}") from e
        except Exception as e:
            self.logger.error(f"✗ 备份过程出错: {e}")
            raise BackupError(f"备份时发生意外错误: {e}") from e

    def restore_backup(self) -> bool:
        """
        从备份恢复客户端

        Returns:
            恢复是否成功

        Raises:
            RestoreError: 恢复失败
        """
        self.logger.warning("正在从备份恢复...")

        if not self.backup_dir.exists():
            raise RestoreError("备份目录不存在,无法恢复")

        try:
            # 删除当前目录内容(保留备份目录和下载的zip)
            for item in self.config.client_dir.iterdir():
                if item.name not in {".backup", "*.zip"} and not item.name.startswith(".update_"):
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        self.logger.warning(f"删除 {item} 失败: {e}")

            # 恢复备份文件
            for item in self.backup_dir.iterdir():
                dest = self.config.client_dir / item.name
                try:
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
                except Exception as e:
                    self.logger.warning(f"恢复 {item} 失败: {e}")

            self.logger.info("恢复成功 ✓")
            return True

        except Exception as e:
            self.logger.error(f"✗ 恢复失败: {e}")
            raise RestoreError(f"恢复操作失败: {e}") from e

    def extract_update(self, zip_file: IO[bytes]) -> bool:
        """
        解压更新包

        Args:
            zip_file: ZIP 文件对象

        Returns:
            解压是否成功

        Raises:
            ExtractionError: 解压失败
        """
        self.logger.info("正在解压更新包...")

        try:
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                # 验证zip文件完整性
                bad_file = zip_ref.testzip()
                if bad_file is not None:
                    raise ExtractionError(f"ZIP文件损坏: {bad_file}")

                # 获取文件列表用于日志
                file_list = zip_ref.namelist()
                self.logger.debug(f"解压 {len(file_list)} 个文件")

                # 解压文件
                zip_ref.extractall(self.config.client_dir)

            return True

        except zipfile.BadZipFile as e:
            self.logger.error(f"✗ ZIP文件格式错误: {e}")
            raise ExtractionError(f"无效的ZIP文件: {e}") from e

        except (IOError, OSError) as e:
            self.logger.error(f"✗ 解压失败: {e}")
            raise ExtractionError(f"解压操作失败: {e}") from e

        except Exception as e:
            self.logger.error(f"✗ 解压过程出错: {e}")
            raise ExtractionError(f"解压时发生意外错误: {e}") from e

    def update_version_file(self, version: str) -> bool:
        """
        更新本地版本文件

        Args:
            version: 新版本号

        Returns:
            更新是否成功
        """
        try:
            version_data = {"version": version, "update_time": datetime.now().isoformat()}

            # 原子性写入
            temp_file = self.version_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)

            temp_file.replace(self.version_file)

            self.logger.info(f"版本更新已完成: {version} ✓")
            return True

        except (IOError, OSError) as e:
            self.logger.error(f"更新版本文件失败: {e}")
            return False

        except Exception as e:
            self.logger.error(f"更新版本文件时出错: {e}")
            return False

    # -------------------------------------------------------------------------
    # 程序启动方法
    # -------------------------------------------------------------------------

    def run_main_program(self, remote_info: VersionInfo) -> None:
        """
        启动主程序,根据文件类型自动选择运行方式

        支持的文件类型:
        - Python 脚本 (.py): 使用 Python 解释器运行
        - 可执行文件 (Linux/Mac: 无后缀或.exe, Windows: .exe): 直接运行
        - Shell/Batch 脚本 (.sh, .bat, .cmd): 使用对应的 shell 运行
        """
        main_script_path = self.config.client_dir / remote_info.entry_point

        if not main_script_path.exists():
            self.logger.error(f"主程序不存在: {main_script_path}")
            return

        self.logger.info(f"正在启动主程序: {remote_info.entry_point}")

        try:
            # 获取文件扩展名
            suffix = main_script_path.suffix.lower()
            is_executable = main_script_path.stat().st_mode & 0o111  # 检查可执行权限

            # 获取传递给当前程序的所有参数(跳过脚本名称)
            program_args = sys.argv[1:]

            # 根据文件类型选择运行方式
            if suffix == ".py":
                # Python 脚本: 解释器 + 脚本路径 + 程序参数
                cmd = [sys.executable, str(main_script_path)] + program_args

            elif suffix in (".sh", ".bat", ".cmd"):
                # Shell/Batch 脚本
                if suffix == ".sh":
                    cmd = ["/bin/bash", str(main_script_path)] + program_args

                else:  # .bat or .cmd (Windows)
                    cmd = [str(main_script_path)] + program_args

            elif suffix == ".exe" or (not suffix and is_executable):
                # 可执行文件 (Windows .exe 或 Linux/Mac 可执行文件)
                cmd = [str(main_script_path)] + program_args

            else:
                raise MainScriptError(f"未能识别的主程序文件类型: {suffix}")

            # Windows 下需要特殊处理
            shell = False
            if sys.platform == "win32":
                # 对于某些命令需要使用 shell
                if suffix in (".bat", ".cmd"):
                    shell = True
                # 对于可执行文件,shell=True 可以确保正确执行
                elif suffix == ".exe":
                    shell = True

            self.logger.debug(f"执行命令: {' '.join(cmd)}")

            # 启动进程,工作目录设置为 client_dir
            process = subprocess.Popen(
                cmd,
                shell=shell,
                cwd=self.config.client_dir,
            )
            self.logger.info(f"主程序已启动 (PID: {process.pid}) ✓")
            if not is_executable:
                process.wait()

        except (subprocess.SubprocessError, OSError) as e:
            self.logger.error(f"启动主程序失败: {e}")
            raise MainScriptError(f"启动主程序失败: {e}") from e

        except Exception as e:
            self.logger.error(f"启动主程序时出现意外错误: {e}")
            raise MainScriptError(f"启动主程序时出现意外错误: {e}") from e

    # -------------------------------------------------------------------------
    # 主要更新流程
    # -------------------------------------------------------------------------

    def check_and_update(self) -> VersionInfo | None:
        """
        检查并执行更新

        Returns:
            更新是否成功
        """
        try:
            local_version = self.get_local_version()  # 获取本地版本
            remote_info = self.get_active_version()  # 获取远程版本

            if not remote_info:
                self.logger.warning("服务器无可用版本")
                return

            elif not local_version:
                self.logger.info(f"发现新版本: 本地未安装 -> {remote_info.version}")

            elif not self.compare_versions(local_version, remote_info.version):
                return remote_info

            # 显示更新信息
            if remote_info.changelog:
                self.logger.info(f"更新日志：{remote_info.changelog}")

            # 下载更新包到内存文件并获取哈希
            temp_zip_file, downloaded_hash = self.download_file(remote_info.download_url)

            # 验证哈希
            if downloaded_hash != remote_info.file_hash:
                raise VerificationError(f"哈希不匹配: 期望 {remote_info.file_hash}, 实际 {downloaded_hash}")

            try:
                # 备份当前版本
                self.backup_client()

                # 解压更新包
                self.extract_update(temp_zip_file)

                # 更新版本文件
                if not self.update_version_file(remote_info.version):
                    self.logger.warning("更新版本文件失败,但不影响使用")

                return remote_info

            except (DownloadError, VerificationError, BackupError, ExtractionError) as e:
                self.logger.error(f"更新失败: {e}")
                self.logger.info("正在尝试恢复备份...")

                try:
                    self.restore_backup()
                    self.logger.info("已恢复到更新前的状态")
                except RestoreError as restore_error:
                    self.logger.error(f"恢复备份失败: {restore_error}")
                    self.logger.error("⚠ 程序可能处于不稳定状态,请手动检查!")

        except VersionCheckError as e:
            self.logger.error(f"版本检查失败: {e}")

        except Exception:
            self.logger.exception("更新过程出现未预期的错误")

    def update_and_run(self) -> None:
        """
        检查更新并在完成后启动主程序
        """
        # 检查并更新
        remote_info = self.check_and_update()

        # 无论更新是否成功,都尝试启动主程序
        if remote_info:
            self.run_main_program(remote_info)
        else:
            self.logger.warning("更新失败或无更新,尝试启动现有版本...")


if __name__ == "__main__":
    # 创建更新器配置
    config = UpdaterConfig(
        check_api_url="http://localhost:8000/api/nuitkal_pack/check/",  # 服务端地址
        client_dir=Path(__file__).parent,
    )

    def progress_callback(downloaded: int, total: int) -> None:
        if total > 0:
            percent = (downloaded / total) * 100
            print(f"下载进度: {percent:.1f}% ({downloaded}/{total} bytes)")
        else:
            print(f"已下载: {downloaded} bytes")

    # 使用统一的进度回调工厂
    config.progress_callback = progress_callback

    # 使用上下文管理器确保资源正确释放
    with UpdaterManager(config) as updater:
        updater.update_and_run()
