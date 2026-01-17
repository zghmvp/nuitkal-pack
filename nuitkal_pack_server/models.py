import hashlib
import uuid
from typing import TYPE_CHECKING, Any, Optional

from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.query import QuerySet


def validate_zip_file(value: Any) -> None:
    """验证上传的文件是否为 ZIP 格式"""
    from django.core.exceptions import ValidationError

    if not value.name.endswith(".zip"):
        raise ValidationError("仅支持 ZIP 格式的更新包文件")


def validate_entry_point(value: str) -> None:
    """验证入口文件扩展名是否合法"""
    from django.core.exceptions import ValidationError

    ALLOWED_EXTENSIONS = [".py", ".sh", ".bat", ".cmd", ".exe"]

    if not value:
        return  # 允许为空

    # 检查文件扩展名
    if not any(value.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValidationError(f"入口文件扩展名必须是以下之一: {', '.join(ALLOWED_EXTENSIONS)}")


class App(models.Model):
    """
    应用模型
    用于管理不同的应用程序,每个应用可以有多个客户端版本
    """

    id = models.CharField(max_length=32, primary_key=True, verbose_name="唯一标识", help_text="系统自动生成的唯一标识符")
    name = models.CharField(max_length=100, unique=True, verbose_name="应用名称", help_text="应用的名称,不可为空", blank=False)
    description = models.TextField(verbose_name="应用说明", help_text="应用的详细说明", blank=True, null=True)
    enable_time = models.DateTimeField(verbose_name="启用时间", help_text="应用开始可用的时间", blank=True, null=True)
    disable_time = models.DateTimeField(verbose_name="停用时间", help_text="应用停止可用的时间,为空表示永不停止", blank=True, null=True)

    if TYPE_CHECKING:
        # 为 IDE 提供类型提示
        client_versions: "QuerySet['ClientVersion']"

    class Meta:
        verbose_name = "应用"
        verbose_name_plural = "应用"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"

    # @classmethod
    # def query_enabled(cls) -> "QuerySet['Self']":
    #     """查询所有已启用的应用"""
    #     return cls.objects.filter(
    #         (models.Q(enable_time__isnull=False) & models.Q(enable_time__lte=timezone.now())) & (models.Q(disable_time__isnull=True) | models.Q(disable_time__gt=timezone.now()))
    #     )

    def save(self, *args: object, **kwargs: object) -> None:
        """
        保存时自动生成 UUID
        """
        if not self.id:
            # 生成唯一的 UUID (使用 uuid4 的 hex 表示)
            self.id = uuid.uuid4().hex
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    def is_available(self) -> bool:
        """
        检查应用是否在可用状态

        可用条件:
        - enable_time <= 当前时间
        - 且 (disable_time 为空 OR disable_time > 当前时间)
        """
        now = timezone.now()

        # 检查启用时间
        if self.enable_time and self.enable_time > now:
            return False

        # 检查停用时间
        if self.disable_time and self.disable_time <= now:
            return False

        return True

    def get_active_version(self) -> Optional["ClientVersion"]:
        """
        获取指定应用的当前激活版本

        Args:
            app: 应用对象

        Returns:
            激活的 ClientVersion 对象,如果不存在则返回 None
        """
        return self.client_versions.filter(is_active=True).first()


class ClientVersion(models.Model):
    """
    客户端版本模型
    用于管理不同版本的客户端更新包
    """

    app = models.ForeignKey(
        App,
        on_delete=models.CASCADE,
        related_name="client_versions",
        verbose_name="所属应用",
        help_text="版本所属的应用",
        db_index=True,  # 添加索引以提高查询性能
    )
    version = models.CharField(max_length=50, verbose_name="版本号", help_text="语义化版本号,如 1.0.1")
    file = models.FileField(max_length=255, upload_to="nuitkal_packs/%Y/%m/", verbose_name="文件路径", help_text="ZIP 格式的更新包文件", validators=[validate_zip_file])
    entry_point = models.CharField(
        max_length=255,
        default="main.py",
        blank=True,
        verbose_name="程序入口路径",
        help_text="更新后的程序启动文件,仅支持 .py, .sh, .bat, .cmd, .exe 格式",
        validators=[validate_entry_point],
    )
    file_size = models.IntegerField(verbose_name="文件大小(字节)", help_text="更新包文件大小", blank=True, null=True)
    file_hash = models.CharField(max_length=64, verbose_name="文件哈希", help_text="SHA256 哈希值,用于校验文件完整性", blank=True)
    upload_time = models.DateTimeField(auto_now_add=True, verbose_name="上传时间", blank=True)
    changelog = models.TextField(verbose_name="更新日志", help_text="版本更新说明")
    is_active = models.BooleanField(default=False, verbose_name="是否为当前推荐版本", help_text="仅一个版本可为 True")

    class Meta:
        verbose_name = "客户端版本"
        verbose_name_plural = "客户端版本"
        ordering = ["-upload_time"]
        # 同一应用下的版本号必须唯一
        constraints = [models.UniqueConstraint(fields=["app", "version"], name="unique_app_version")]

    def __str__(self) -> str:
        return f"Client v{self.version} {'(Active)' if self.is_active else ''}"

    def save(self, *args: object, **kwargs: object) -> None:
        """
        保存时确保同一应用只有一个 active 版本，并自动计算文件大小和哈希值
        """
        # 如果是新上传的文件，计算文件大小和哈希值
        # 获取文件大小
        self.file_size = self.file.size
        # 计算文件哈希值
        self.file_hash = self.calculate_file_hash(self.file.file)

        if self.is_active:
            # 将同一应用下其他版本的 is_active 设为 False
            ClientVersion.objects.filter(app=self.app, is_active=True).update(is_active=False)
        super().save(*args, **kwargs)  # type: ignore

    def set_active(self) -> None:
        """
        设置当前版本为激活版本
        同时将同一应用下其他版本的 is_active 设为 False
        """
        # 将同一应用下其他版本的 is_active 设为 False
        self.app.client_versions.filter(is_active=True).update(is_active=False)
        # 设置当前版本为激活版本
        self.is_active = True
        self.save()

    def calculate_file_hash(self, file_object) -> str:
        """
        计算文件的 SHA256 哈希值
        支持文件路径字符串、InMemoryUploadedFile 等文件对象
        """
        sha256_hash = hashlib.sha256()

        # 如果是字符串路径，打开文件
        if isinstance(file_object, str):
            with open(file_object, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
        else:
            # 处理 InMemoryUploadedFile 等文件对象
            # 重置文件指针到开始位置
            file_object.seek(0)
            for byte_block in iter(lambda: file_object.read(4096), b""):
                sha256_hash.update(byte_block)
            # 重置文件指针，以便后续读取
            file_object.seek(0)

        return sha256_hash.hexdigest()
