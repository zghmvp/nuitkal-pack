# 全局环境执行安装 nuitka
# ============= Mac ============= #
# pip3 install --break-system-packages nuitka
# ============= Windows ============= #
# pip install nuitka

import hashlib
import io
import logging
import platform
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, MutableMapping, cast, overload

import diskcache
import pathspec

# 日志配置
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def calculate_hash(file_path: Path | bytes | str, buffer_size: int = 65536) -> str:
    """计算文件的哈希值(内存优化版,适用于大文件)

    Args:
        file_path: 文件路径
        buffer_size: 读取缓冲区大小,默认64KB

    Returns:
        文件的MD5哈希值

    """
    md5 = hashlib.sha256()

    if isinstance(file_path, str):
        file_path = file_path.encode("utf-8")

    if isinstance(file_path, Path):
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(buffer_size), b""):
                md5.update(chunk)
    else:
        md5.update(file_path)

    return md5.hexdigest()


@dataclass
class BuildFile:
    full_path: Path
    rel_path: Path
    jump_first: bool = False

    def __post_init__(self):
        with self.full_path.open("rb") as f:
            if self.jump_first:
                next(f)
            self.data = f.read()

        self.name = self.rel_path.name
        self.file_hash = calculate_hash(self.data)  # 文件哈希
        self.identity_hash = calculate_hash(f"{self.rel_path.as_posix()}:{self.file_hash}")  # (文件哈希 + 路径)计算出来的唯一哈希


def compile_with_nuitka(
    full_path: Path,
    rel_path: Path,
    *,
    build_dir: Path | None = None,
    options: list[str] | tuple[str, ...] = (),
    cache: diskcache.Cache | None = None,
    logger: logging.Logger | None = None,
) -> tuple[BuildFile, BuildFile]:
    """使用Nuitka编译Python文件为.pyd与.pyi文件"""
    # 使用传入的哈希值或计算新的哈希值
    file_hash = calculate_hash(full_path)
    cache_key = f"nuitka:{full_path}:{file_hash}:{':'.join(options)}"

    # 检查缓存
    if cache is not None:
        try:
            if cache_key in cache:
                return cast("tuple[BuildFile, BuildFile]", cache[cache_key])

        except Exception as e:
            if logger:
                logger.warning(f"缓存读取失败: {e},将重新编译")
            # 继续执行编译流程

    if logger:
        logger.info(f"× 缓存未命中, 开始编译: {full_path.name}")

    with TemporaryDirectory() as temp_dir:
        output_dir = build_dir if build_dir else Path(temp_dir)

        match platform.system():
            case "Windows":
                nuitka_path = Path(sys.executable).parent / "nuitka.cmd"
            case _:
                nuitka_path = Path(sys.executable).parent / "nuitka"

        # 构建Nuitka编译命令
        cmd = [
            nuitka_path,
            "--module",
            str(full_path),
            f"--output-dir={output_dir}",
            "--nofollow-imports",  # 不编译依赖
            "--remove-output",  # 编译完成后删除中间文件（如 .build 目录），节省磁盘空间
            # "--no-pyi-file",  # 不生成.pyi文件
            *options,
        ]

        # 执行编译命令
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,  # 是否抛出异常
            encoding="utf-8",
        )

        # 从输出中查找生成的.pyd文件路径
        stdout_lines = result.stdout.splitlines()
        for line in reversed(stdout_lines):
            match platform.system():
                case "Windows":
                    pyd_match = re.search(r"^Nuitka: Successfully created '.+?([^\\/]+?.pyd)'", line)
                case _:
                    pyd_match = re.search(r"^Nuitka: Successfully created '.+?([^\\/]+?.so)'", line)

            if not pyd_match:
                continue

            pyd_filename = pyd_match.group(1)
            pyd_path = output_dir / pyd_filename
            pyi_path = output_dir / full_path.with_suffix(".pyi").name

            if not pyi_path.exists():
                raise FileNotFoundError(f"生成的.pyi文件不存在: {pyi_path}")

            pyd_file = BuildFile(full_path=pyd_path, rel_path=rel_path.with_name(pyd_path.name))
            pyi_file = BuildFile(full_path=pyi_path, rel_path=rel_path.with_name(pyi_path.name))

            # 将编译结果存入缓存
            if cache is not None:
                try:
                    cache[cache_key] = pyd_file, pyi_file
                    if logger:
                        logger.info(f"✓ 已缓存编译结果: {full_path.name}")

                except Exception as e:
                    if logger:
                        logger.warning(f"缓存存储失败: {e}")

            return pyd_file, pyi_file

        # 如果没有找到成功创建的消息,抛出错误
        error_msg = f"Nuitka编译失败\n{' '.join(cmd)}"
        if result.stdout.strip():
            error_msg += f"\n\n输出:\n{result.stdout}"
        raise RuntimeError(error_msg)


class PythonPackager:
    """Python应用打包器"""

    def __init__(
        self,
        source_dir: Path,
        *,
        log_level: int = logging.INFO,
        cache_dir: Path | str | None = None,
        enable_cache: bool = True,
    ):
        """初始化Python打包器

        Args:
            source_dir: 源代码目录
            log_level: 日志级别
            cache_dir: 缓存目录,默认为源目录下的.packager_cache
            enable_cache: 是否启用缓存

        """
        self.source_dir: Path = Path(source_dir).absolute()

        self.core_map: MutableMapping[str, BuildFile] = {}
        self.static_map: MutableMapping[str, BuildFile] = {}
        self.user_map: MutableMapping[str, MutableMapping[str, BuildFile]] = defaultdict(dict)

        # 初始化日志
        self.logger = self._setup_logger(log_level)

        # 初始化缓存
        if enable_cache:
            if cache_dir is None:
                cache_dir = self.source_dir / ".packager_cache"
            self.cache = diskcache.Cache(cache_dir)
            self.logger.info(f"缓存目录: {cache_dir}")
        else:
            self.cache = None
            self.logger.info("缓存已禁用")

    def _setup_logger(self, level: int = logging.INFO) -> logging.Logger:
        """设置日志记录器

        Args:
            level: 日志级别，默认为INFO

        Returns:
            配置好的日志记录器

        """
        logger = logging.getLogger("zghmvp-packager")
        logger.setLevel(level)

        # 清除已存在的处理器
        if logger.handlers:
            logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def __del__(self):
        """析构函数,确保缓存正确关闭"""
        if hasattr(self, "cache") and self.cache is not None:
            # with suppress(Exception):
            self.cache.close()

    def rglob_exclude(self, root: Path, patterns: list[str] | tuple[str, ...] = ("*",), exclude_files: list[str] | tuple[str, ...] = ()) -> Iterator[Path]:
        """递归查找匹配 pattern 的文件,跳过排除的目录"""
        # 合并默认排除模式和用户自定义排除模式
        default_excludes = ["/venv", "/.venv", "/env", "**/__pycache__", "**/__MACOSX"]
        exclude_dir_patterns = list(set(exclude_files) | set(default_excludes))

        spec_include = pathspec.GitIgnoreSpec.from_lines(patterns)
        spec_exclude = pathspec.GitIgnoreSpec.from_lines(exclude_dir_patterns)

        for full_path in root.iterdir():
            rel_path = full_path.relative_to(self.source_dir)

            # 跳过被排除的路径
            if spec_exclude.match_file(rel_path):
                continue

            if full_path.is_dir():
                # 递归处理子目录
                yield from self.rglob_exclude(full_path, patterns, exclude_dir_patterns)
            elif spec_include.match_file(rel_path):
                yield full_path

    def compile(
        self,
        rglob_pattern: list[str] | tuple[str, ...] = ("*",),
        *,
        build_dir: Path | None = None,
        static_files: list[str] | tuple[str, ...] = (),
        exclude_files: list[str] | tuple[str, ...] = (),
        nuitka_options: list[str] | tuple[str, ...] = (),
    ) -> None:
        """编译并分类源文件"""
        self.logger.info(f"开始扫描目录: {self.source_dir}")

        spec_static = pathspec.GitIgnoreSpec.from_lines(static_files)

        # 用于统计编译信息
        total_files = 0

        # 排除缓存目录
        if self.cache:
            cache_dir = Path(self.cache.directory).relative_to(self.source_dir)
            exclude_files = (*exclude_files, f"/{cache_dir}")

        for full_path in self.rglob_exclude(self.source_dir, rglob_pattern, exclude_files):
            rel_path = full_path.relative_to(self.source_dir)

            # 处理静态文件
            if spec_static.match_file(rel_path):
                self.logger.info(f"发现静态文件: {rel_path}")
                file = BuildFile(full_path, rel_path)
                self.static_map[file.identity_hash] = file
                continue

            # 处理Python文件
            if full_path.suffix == ".py":
                total_files += 1

                # 只读取第一行进行标签匹配判断,避免加载整个文件
                with full_path.open("r", encoding="utf-8") as f:
                    first_line = f.readline()

                pyd_match = re.search(r"\spyd[\s$]", first_line)
                core_match = re.search(r"\score[\s$]", first_line)
                user_match = re.findall(r"\suser-(.+?)(?=\s|$)", first_line)

                if pyd_match:
                    self.logger.info(f"发现编译文件[pyd]: {rel_path}")
                    pyd_file, pyi_file = compile_with_nuitka(full_path, rel_path, build_dir=build_dir, options=nuitka_options, cache=self.cache, logger=self.logger)
                    self.core_map[pyd_file.identity_hash] = pyd_file
                    self.core_map[pyi_file.identity_hash] = pyi_file

                elif core_match:
                    self.logger.info(f"发现核心文件[py]: {rel_path}")
                    file = BuildFile(full_path, rel_path, jump_first=True)
                    self.core_map[file.identity_hash] = file

                elif user_match:
                    self.logger.info(f"发现用户文件[py]: {rel_path} (用户: {'、'.join(user_match)})")
                    for user_name in user_match:
                        file = BuildFile(full_path, rel_path, jump_first=True)
                        self.user_map[user_name][file.identity_hash] = file

        # 输出编译统计信息
        self.logger.info(f"编译完成: 共编译 {total_files} 个Python文件")

    @overload
    def to_zip(self, user_name: str) -> io.BytesIO: ...
    @overload
    def to_zip(self, user_name: None = None) -> MutableMapping[str, io.BytesIO]: ...
    def to_zip(self, user_name: str | None = None, exclude_hashes: list[str] | tuple[str, ...] = ()) -> MutableMapping[str, io.BytesIO] | io.BytesIO:
        """创建ZIP压缩包

        Args:
            user_name: 指定用户名称,如果为None则返回所有用户的ZIP包
            exclude_hashes: 要排除的文件哈希列表；可以直接传入整个服务器中获取的hash列表，从而只打包有更新的文件(注意不是文件哈希，是文件哈希后与相对路径再次计算得到的哈希值)

        Returns:
            单个用户的ZIP包或所有用户的ZIP包字典

        """
        self.logger.info("开始创建ZIP包")

        results: MutableMapping[str, io.BytesIO] = {}

        # 为每个用户创建ZIP包
        for name in self.user_map:
            # 合并文件: 核心文件 + 静态文件 + 用户特定文件
            file_map = {**self.core_map, **self.static_map, **self.user_map[name]}

            io_zip = io.BytesIO()
            with zipfile.ZipFile(io_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for hash_id, file in file_map.items():
                    if hash_id in exclude_hashes:
                        continue

                    zf.writestr(str(file.rel_path), file.data)

            # 重置指针以便后续读取
            io_zip.seek(0)
            results[name] = io_zip

        # 返回指定用户的ZIP包或所有用户的ZIP包
        return results[user_name] if user_name else results
