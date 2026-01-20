import hashlib
import io
import os
import tempfile
import zipfile

from django.contrib import admin
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.utils.html import format_html, mark_safe  # type: ignore[attr-defined]

from .models import App, AppVersion, VersionFile


class VersionPackager:
    """版本打包器"""

    def __init__(self, app: App, version: str, entry_point: str, changelog: str = ""):
        self.app = app
        self.version = version
        self.entry_point = entry_point
        self.changelog = changelog
        self.file_manifest = []

    def process_zip_file(self, zip_file: UploadedFile, app_version: AppVersion | None = None) -> AppVersion:
        """处理上传的 ZIP 文件,创建新版本或更新已有版本"""
        if app_version is None:
            app_version = AppVersion.objects.create(app=self.app, version=self.version, entry_point=self.entry_point, changelog=self.changelog, is_active=False)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            for chunk in zip_file.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        try:
            with zipfile.ZipFile(temp_path, "r") as zip_ref:
                for file_path in zip_ref.namelist():
                    if file_path.endswith("/") or file_path.startswith("__MACOSX/"):
                        continue

                    with zip_ref.open(file_path) as extracted_file:
                        content = extracted_file.read()
                        content_hash = hashlib.sha256(content).hexdigest()

                        if not VersionFile.objects.filter(id=content_hash).exists():
                            django_file = File(io.BytesIO(content), name=content_hash)
                            VersionFile.objects.create(id=content_hash, version=app_version, size=len(content), file=django_file)

                        self.file_manifest.append({"hash": content_hash, "path": file_path})

            app_version.file_manifest = self.file_manifest
            app_version.save()
            return app_version

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    """应用管理"""

    list_display = ["name", "description", "is_available", "enable_time", "disable_time", "created_at"]
    list_filter = ["enable_time", "disable_time"]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (("基础信息", {"fields": ("id", "name", "description", "enable_time", "disable_time")}),)

    def is_available(self, obj):
        """显示应用是否可用"""
        return obj.is_available()


@admin.register(AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    """客户端版本管理"""

    list_display = ("app", "version", "is_active", "get_file_count", "get_total_size_display", "entry_point", "upload_time")
    list_filter = ("app", "is_active", "upload_time")
    search_fields = ("version", "changelog", "app__name")
    readonly_fields = ("id", "upload_time", "created_at", "get_file_count", "get_total_size_display", "show_file_manifest")

    fieldsets = (
        ("基础信息", {"fields": ("app", "version", "entry_point", "is_active", "changelog")}),
        (
            "文件上传",
            {
                "fields": ("get_file_count", "get_total_size_display", "show_file_manifest"),
                "description": "上传应用 ZIP 包,系统将自动处理文件并创建记录",
            },
        ),
    )

    def get_file_count(self, obj: AppVersion):
        """获取文件数量"""
        return obj.get_file_count()

    def get_total_size_display(self, obj: AppVersion):
        """获取总大小(显示为 MB)"""
        size = obj.get_total_size()
        if size == 0:
            return "0 MB"
        return f"{size / 1024 / 1024:.2f} MB"

    def show_file_manifest(self, obj: AppVersion):
        """显示文件清单"""
        if not obj.file_manifest:
            return "暂无文件"

        html = '<div style="max-height: 300px; overflow-y: auto;">'
        html += '<table style="width: 100%; border: 1px solid #ddd;">'
        html += '<tr style="background: #f0f0f0;"><th>哈希</th><th>路径</th></tr>'

        for key, path in obj.file_manifest.items():
            html += format_html("<tr><td>{}</td><td>{}</td></tr>", key, path)

        if len(obj.file_manifest) > 10:
            html += format_html('<tr><td colspan="2" style="text-align: center; color: #888;">... 还有 {} 个文件</td></tr>', len(obj.file_manifest) - 10)

        html += "</table></div>"
        return mark_safe(html)

    def delete_model(self, request, obj):
        """删除模型时的确认"""
        file_count = obj.get_file_count()
        super().delete_model(request, obj)
        self.message_user(request, f"已删除版本 {obj.version} 及其 {file_count} 个文件记录")


@admin.register(VersionFile)
class VersionFileAdmin(admin.ModelAdmin):
    """版本文件管理"""

    list_display = ["id", "size", "size_display", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["id"]
    readonly_fields = ["id", "size", "size_display", "file", "created_at"]

    def size_display(self, obj):
        """显示文件大小"""
        if obj.size < 1024:
            return f"{obj.size} B"
        if obj.size < 1024 * 1024:
            return f"{obj.size / 1024:.2f} KB"
        return f"{obj.size / 1024 / 1024:.2f} MB"


# 自定义 Admin 标题
admin.site.site_header = "Nuitkal Pack 管理后台"
admin.site.site_title = "Nuitkal Pack"
admin.site.index_title = "增量更新系统管理"
