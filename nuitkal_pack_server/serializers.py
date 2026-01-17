from rest_framework import serializers

from .models import App, ClientVersion


class AppSerializer(serializers.ModelSerializer):
    """应用序列化器"""

    is_available = serializers.BooleanField(read_only=True, help_text="应用是否可用")

    class Meta:
        model = App
        fields = [
            "id",
            "name",
            "description",
            "enable_time",
            "disable_time",
            "is_available",
        ]
        read_only_fields = [
            "id",
            "is_available",
        ]


class ClientActiveSerializer(serializers.ModelSerializer):
    version = serializers.CharField(help_text="版本号", required=True)

    class Meta:
        model = ClientVersion


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientVersion
        fields = "__all__"


class ClientUploadSerializer(serializers.ModelSerializer):
    """版本上传序列化器"""

    class Meta:
        model = ClientVersion
        fields = [
            "app",
            "version",
            "file",
            "entry_point",
            "changelog",
            "is_active",
        ]

    def validate(self, attrs):
        """验证上传数据"""
        # 验证 App 是否存在
        app: App | None = attrs.get("app")
        if not app:
            raise serializers.ValidationError({"app": "指定的 App 不存在"})

        # 验证版本是否已存在
        version = attrs.get("version")
        if app.client_versions.filter(version=version).exists():
            raise serializers.ValidationError({"version": f"版本 {version} 在该应用下已存在"})

        # 验证文件格式
        file = attrs.get("file")
        if file and not file.name.endswith(".zip"):
            raise serializers.ValidationError({"file": "仅支持 ZIP 格式的更新包"})

        return attrs
