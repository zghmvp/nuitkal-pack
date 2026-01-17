"""DRF Viewsets 视图"""

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import App
from .serializers import AppSerializer, ClientActiveSerializer, ClientSerializer, ClientUploadSerializer


class AppViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    应用视图集

    list: 获取可用应用列表
    retrieve: 获取应用详情
    """

    queryset = App.objects.all()
    serializer_class = AppSerializer
    lookup_field = "id"

    def get_queryset(self):
        """重写查询集,默认只返回可用应用"""
        queryset = super().get_queryset()

        # 检查是否要过滤可用应用
        is_available = self.request.query_params.get("is_available")
        if is_available is None:
            # 默认只返回可用应用
            from django.db.models import Q
            from django.utils import timezone

            now = timezone.now()
            queryset = queryset.filter(Q(enable_time__lte=now) & (Q(disable_time__isnull=True) | Q(disable_time__gt=now)))

        return queryset

    @action(detail=True, methods=["get"], url_path="active")
    def get_active_version(self, request, id):
        """获取所有激活版本"""
        app: App = self.get_object()
        client = app.get_active_version()
        if not client:
            return Response(
                {"error": f"应用 {app.name} 没有激活版本"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="list")
    def get_list_versions(self, request, id):
        app: App = self.get_object()
        clients = app.client_versions.all()

        serializer = ClientSerializer(clients, many=True)

        return Response(
            {"data": serializer.data, "message": "版本列表获取成功"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="upload", serializer_class=ClientUploadSerializer, parser_classes=[MultiPartParser, FormParser])
    def upload_version(self, request, id):
        app: App = self.get_object()

        serializer = self.get_serializer(dict(request.data, app=app))
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # 检查版本是否已存在
        if app.client_versions.filter(version=request.data["version"]).exists():
            return Response(
                {"error": f"版本 {request.data['version']} 在该应用下已存在"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 创建版本记录
        client_version = serializer.save()

        serializer = self.get_serializer(client_version)
        return Response(
            {"message": "版本上传成功", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], serializer_class=ClientActiveSerializer, url_path="set_active")
    def set_active(self, request, id):
        serializer = self.get_serializer(request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        client_version = serializer.data["client_version"]
        app: App = self.get_object()
        client = app.client_versions.get(version=client_version)

        if not client:
            return Response(
                {"error": f"版本 {client_version} 不存在"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 设置为激活版本
        client.set_active()

        return Response(
            {"message": f"版本 {client_version.version} 已设为激活版本"},
            status=status.HTTP_200_OK,
        )
