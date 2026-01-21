import json
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, cast

from django.core.files.base import ContentFile
from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from nuitkal_pack_server.tools import zipfile
from nuitkal_pack_server.tools.hash_utils import calculate_file_hash

from .models import App, AppVersion, VersionFile
from .serializers import AppSerializer, AppVersionSerializer
from .tools.version_service import VersionService

if TYPE_CHECKING:
    from rest_framework.request import Request


class AppViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """应用管理视图集"""

    authentication_classes = ()  # 可选，完全禁用认证
    permission_classes = (AllowAny,)

    queryset = App.objects.all()
    serializer_class = AppSerializer
    lookup_field = "pk"

    def get_version(self, version: str) -> AppVersion:
        """获取应用指定版本"""
        if not version:
            raise ValueError("版本号不能为空")

        app_version = AppVersion.objects.filter(app_id=id, version=version).first()
        if not app_version:
            raise ValueError(f"该版本[{version}]不存在")

        return app_version

    def get_app_and_active_version(self) -> tuple[App, AppVersion]:
        """获取应用及其激活版本"""
        app = cast("App", self.get_object())
        active_version = app.get_active_version()
        if not active_version:
            raise ValueError("该应用暂无激活版本")
        return app, active_version

    def handle_exception(self, exc: Exception) -> Response:
        """处理异常"""
        if isinstance(exc, ValueError):
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)

    def get_queryset(self) -> QuerySet[App]:
        """重写查询集, 默认只返回可用应用"""
        queryset = super().get_queryset()
        is_available = self.request.query_params.get("is_available")

        if is_available is None:
            now = timezone.now()
            queryset = queryset.filter(Q(enable_time__lte=now) & (Q(disable_time__isnull=True) | Q(disable_time__gt=now)))

        return queryset

    @action(detail=True, methods=["get"], url_path="list")
    def get_versions(self, request: "Request", pk: str) -> Response:
        """获取应用的所有版本"""
        app = cast("App", self.get_object())
        versions = app.appversion_set.all()
        serializer = AppVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="active")
    def get_active(self, request: "Request", pk: str) -> Response:
        """获取应用的激活版本"""
        _, active_version = self.get_app_and_active_version()
        serializer = AppVersionSerializer(active_version)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="check-update")
    def check_update(self, request: "Request", pk: str) -> Response:
        """检查更新（增量/全量）

        增量更新：传入本地版本号，返回变动清单
        全量更新：版本号为空，返回完整文件清单
        """
        app: App = self.get_object()
        current_version = request.query_params.get("version")
        update_info = VersionService.get_update_info(app, current_version)
        return Response(update_info)

    @action(detail=True, methods=["post"], url_path="upload-zip")
    def upload_zip(self, request: "Request", pk: str) -> Response:
        """上传 ZIP 包"""
        app: App = self.get_object()
        file = request.FILES.get("file")
        version = request.data.get("version")
        entry_point = request.data.get("entry_point", "main.py")
        changelog = request.data.get("changelog", "")
        is_active = request.data.get("is_active", "false").lower() == "true"

        # 基础验证
        if not file:
            return Response({"error": "缺少文件"}, status=status.HTTP_400_BAD_REQUEST)

        if not version:
            return Response({"error": "缺少版本号"}, status=status.HTTP_400_BAD_REQUEST)

        if app.appversion_set.filter(version=version).exists():
            return Response({"error": f"版本[{version}]已存在"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ZIP 格式验证
            if not file.name.endswith(".zip"):
                return Response({"error": "请上传 ZIP 格式的文件"}, status=status.HTTP_400_BAD_REQUEST)

            # 使用服务层处理上传
            zip_file = zipfile.ZipFile(BytesIO(file.read()))
            file_manifest: dict[str, str] = {}
            for path in zip_file.namelist():
                file = zip_file.read(path)
                hash_id = calculate_file_hash(file)
                posix_path = Path(path).as_posix()
                file_manifest[posix_path] = hash_id

                if not VersionFile.objects.filter(id=hash_id).exists():
                    VersionService.upload_file(ContentFile(file, name=Path(path).name))

            VersionService.create_version(app=app, version=version, entry_point=entry_point, changelog=changelog, is_active=is_active, file_manifest=file_manifest)

            App.objects.filter(id=app.pk).update(updated_at=timezone.now())
            return Response(
                {
                    "message": "版本上传成功",
                    "version": version,
                    "is_active": is_active,
                },
            )

        except zipfile.BadZipFile:
            return Response({"error": "无效的 ZIP 文件"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="upload-file")
    def upload_file(self, request: "Request", pk: str) -> Response:
        """上传 单个文件"""
        file = request.FILES.get("file")  # type: ignore[assignment]
        if not file:
            return Response({"error": "缺少文件"}, status=status.HTTP_400_BAD_REQUEST)

        file = VersionService.upload_file(file)
        return Response({"message": "文件上传成功", "id": file.id, "url": file.file.url})

    @action(detail=True, methods=["post"], url_path="create-version")
    def create_version(self, request: "Request", pk: str) -> Response:
        """上传 多个文件"""
        app: App = self.get_object()
        version = request.data.get("version")
        entry_point = request.data.get("entry_point", "main.py")
        changelog = request.data.get("changelog", "")
        is_active = request.data.get("is_active", "false").lower() == "true"
        file_manifest = json.loads(request.data.get("file_manifest", "{}"))

        if isinstance(file_manifest, dict):
            VersionService.create_version(app=app, version=version, entry_point=entry_point, changelog=changelog, is_active=is_active, file_manifest=file_manifest)
        else:
            return Response({"error": "file_manifest 必须是字典"}, status=status.HTTP_400_BAD_REQUEST)

        App.objects.filter(id=app.pk).update(updated_at=timezone.now())
        return Response(
            {
                "message": "版本上传成功",
                "version": version,
                "is_active": is_active,
            },
        )

    @action(detail=False, methods=["post"], url_path="check-files")
    def check_files(self, request: "Request") -> Response:
        """检查文件是否存在"""
        file_hashes = request.data.get("file_hashes", [])
        if not isinstance(file_hashes, list):
            return Response({"error": "file_hashes 必须是列表"}, status=status.HTTP_400_BAD_REQUEST)

        existing_files = VersionFile.objects.filter(id__in=file_hashes).values_list("id", flat=True)
        return Response(
            {
                "missing_files": list(set(existing_files) - set(file_hashes)),
                "existing_files": existing_files,
            }
        )
