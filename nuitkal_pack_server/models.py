import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Optional, Union

from django.db import models
from django.db.models import Sum
from django.utils import timezone

# 类型定义导入

if TYPE_CHECKING:
    from typing import Self

    from .tools.types import FileInfo, IncrementalUpdateInfo


class App(models.Model):
    """应用模型 - 管理不同的应用程序"""

    if TYPE_CHECKING:
        appversion_set: models.QuerySet["AppVersion"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="应用ID")

    name = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="应用名称")

    description = models.TextField(default="", verbose_name="应用说明")

    enable_time = models.DateTimeField(null=True, blank=True, verbose_name="启用时间")

    disable_time = models.DateTimeField(null=True, blank=True, verbose_name="停用时间")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "应用"

        verbose_name_plural = "应用列表"

        ordering = ("-enable_time",)

    def __str__(self):
        return self.name

    def is_available(self) -> bool:
        """检查应用是否在可用状态"""
        now = timezone.now()

        if self.enable_time and self.enable_time > now:
            return False

        if self.disable_time and self.disable_time <= now:
            return False

        return True

    def get_active_version(self) -> Optional["AppVersion"]:
        """获取当前激活的版本"""
        return self.appversion_set.filter(is_active=True).first()

    def get_all_core_files(self, old_file_hash_list: dict | None) -> "IncrementalUpdateInfo":
        """获取更新所需的文件清单, 传入列表获取增量更新, None则是全量更新"""
        active_version = self.get_active_version()

        if active_version is not None:
            return active_version.get_all_core_files(old_file_hash_list)

        return {"add": [], "keep": [], "delete": []}

    def set_active(self, version: Union[str, "AppVersion"]) -> None:
        """设置指定版本为激活状态"""
        if isinstance(version, str):
            version = self.appversion_set.get(version=version)
        version.save()

    def get_version_files(self) -> list["FileInfo"]:
        """获取所有包含的文件信息"""
        active_version = self.get_active_version()

        if active_version is not None:
            return active_version.get_files()

        return []


class AppVersion(models.Model):
    """客户端版本模型 - 管理不同版本的更新包"""

    app = models.ForeignKey("App", on_delete=models.CASCADE, related_name="appversion_set", verbose_name="所属应用")

    version = models.CharField(max_length=50, db_index=True, verbose_name="版本号")

    entry_point = models.CharField(max_length=255, verbose_name="程序入口路径")

    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    changelog = models.TextField(default="", verbose_name="更新日志")

    is_active = models.BooleanField(default=False, db_index=True, verbose_name="是否激活")

    file_manifest = models.JSONField(default=dict, verbose_name="文件清单")  # {文件相对路径: 文件哈希值}

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "客户端版本"

        verbose_name_plural = "客户端版本列表"

        ordering = ("-upload_time",)

        unique_together = ("app", "version")

    def __str__(self) -> str:
        """返回应用版本的字符串表示"""
        return f"{self.app.name} - {self.version}"

    def save(self, *args: list, **kwargs: dict) -> None:
        """重写保存方法,确保 is_active 唯一性"""
        if self.is_active:
            AppVersion.objects.filter(app=self.app, is_active=True).exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)

    def set_active(self) -> None:
        """设置为激活状态"""
        self.is_active = True
        self.save()

    def get_all_core_files(self, old_file_manifest: dict | None) -> "IncrementalUpdateInfo":
        """计算增量更新文件清单

        Args:
            old_file_manifest: 旧版本的文件清单


        Returns:
            包含 add、keep、delete 的增量更新信息

            所有字段都使用统一的 FileInfo 类型

        """
        if old_file_manifest is None:
            old_file_manifest = {}

        all_file_manifest = dict(old_file_manifest, **self.file_manifest)

        def format_(path_list: set[str]) -> list["FileInfo"]:
            results = []

            for path in path_list:
                hash_id = all_file_manifest[path]

                file = VersionFile.get(hash_id).file

                results.append({"hash": hash_id, "path": path, "url": file.url, "size": file.size})
            return results

        all_file_manifest = dict(old_file_manifest, **self.file_manifest)

        # 需要添加的文件（包含 size）

        add_files = format_(set(self.file_manifest.keys()) - set(old_file_manifest.keys()))

        # 可以保留的文件（统一使用 FileInfo，size 设为 0）

        keep_files = format_(set(self.file_manifest.keys()) & set(old_file_manifest.keys()))

        # 需要删除的文件（统一使用 FileInfo，从旧清单中获取完整信息）

        delete_files = format_(set(old_file_manifest.keys()) - set(self.file_manifest.keys()))

        return {"add": add_files, "keep": keep_files, "delete": delete_files}

    def get_file_count(self) -> int:
        """获取版本包含的文件数量"""
        return len(self.file_manifest) if self.file_manifest else 0

    def get_total_size(self) -> int:
        """获取版本总大小(字节)"""
        if not self.file_manifest:
            return 0

        return VersionFile.objects.filter(id__in=self.file_manifest.keys()).aggregate(total=Sum("size"))["total"] or 0

    def get_files(self) -> list["FileInfo"]:
        """获取版本包含的所有文件信息"""
        return self.get_all_core_files(None)["add"] + self.get_all_core_files(None)["keep"]


class VersionFile(models.Model):
    """文件信息模型 - 存储文件内容"""

    id = models.CharField(max_length=64, primary_key=True, verbose_name="文件Hash")

    file = models.FileField(upload_to="nuitkal-pack", verbose_name="文件")

    name = models.CharField(max_length=255, verbose_name="文件名")

    size = models.BigIntegerField(verbose_name="文件大小(字节)")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        verbose_name = "版本文件"

        verbose_name_plural = "版本文件列表"

        ordering = ("-created_at",)

    def __str__(self) -> str:
        """返回文件的字符串表示"""
        return f"{self.id[:16]}... ({self.size} bytes) "

    @classmethod
    @lru_cache(maxsize=1024)
    def get(cls, pk: str) -> "Self":
        """获取文件URL"""
        return cls.objects.get(id=pk)
