from rest_framework import serializers

from .models import App, AppVersion


class AppVersionSerializer(serializers.ModelSerializer):
    """客户端版本序列化器"""

    file_count = serializers.SerializerMethodField()

    total_size = serializers.SerializerMethodField()

    files = serializers.SerializerMethodField()

    class Meta:
        model = AppVersion

        fields = ("id", "version", "entry_point", "upload_time", "changelog", "is_active", "file_count", "total_size", "created_at", "files")

    def get_file_count(self, obj: AppVersion) -> int:
        """获取文件数量"""
        return obj.get_file_count()

    def get_total_size(self, obj: AppVersion) -> int:
        """获取总文件大小"""
        return obj.get_total_size()

    def get_files(self, obj: AppVersion) -> list[dict]:
        """获取所有包含的文件信息"""
        return obj.get_files()


class AppSerializer(serializers.ModelSerializer):
    """应用序列化器"""

    active_version = serializers.SerializerMethodField()

    class Meta:
        model = App

        fields = ("id", "name", "description", "enable_time", "disable_time", "active_version", "created_at", "updated_at")

    def get_active_version(self, obj: App) -> dict | None:
        """获取激活版本"""
        active_version = obj.get_active_version()

        return dict(AppVersionSerializer(active_version).data) if active_version else None
