from django.contrib import admin

from .models import App, ClientVersion


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    """
    应用管理后台
    """

    list_display = ["name", "id", "enable_time", "disable_time", "is_available_display"]
    list_filter = ["enable_time", "disable_time"]
    search_fields = ["name", "id", "description"]
    readonly_fields = ["id"]
    ordering = ["name"]

    fieldsets = (
        ("基本信息", {"fields": ("name", "id")}),
        ("时间设置", {"fields": ("enable_time", "disable_time")}),
        ("应用说明", {"fields": ("description",)}),
    )

    def is_available_display(self, obj: App) -> str:
        """显示应用是否可用"""
        return "✓ 可用" if obj.is_available() else "✗ 不可用"

    is_available_display.short_description = "可用状态"  # type: ignore[attr-defined]


@admin.register(ClientVersion)
class ClientVersionAdmin(admin.ModelAdmin):
    """
    客户端版本管理后台
    """

    list_display = ["app", "version", "file_size", "upload_time", "is_active", "get_file_size_mb"]
    list_filter = ["app", "is_active", "upload_time"]
    search_fields = ["version", "changelog", "app__name"]
    readonly_fields = ["upload_time", "file_hash", "file_size"]
    ordering = ["-upload_time"]

    fieldsets = (
        ("基本信息", {"fields": ("app", "version", "is_active")}),
        ("文件信息", {"fields": ("file", "entry_point", "file_size", "file_hash")}),
        ("更新日志", {"fields": ("changelog",)}),
        ("元数据", {"fields": ("upload_time",), "classes": ("collapse",)}),
    )

    def get_file_size_mb(self, obj: ClientVersion) -> str:
        """显示文件大小(MB)"""
        if obj.file_size is None:
            return "N/A"
        return f"{obj.file_size / 1024 / 1024:.2f} MB"

    get_file_size_mb.short_description = "文件大小"  # type: ignore[attr-defined]
