from typing import Any, List

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# 创建路由器
router = DefaultRouter()

# 注册 ViewSets
router.register(r"apps", views.AppViewSet, basename="app")

urlpatterns: List[Any] = [
    # 使用 DRF Router 的路由
    path("", include(router.urls)),
]
