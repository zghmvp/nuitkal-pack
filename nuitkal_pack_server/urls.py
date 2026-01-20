from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# 创建路由器
router = DefaultRouter()
router.register(r"apps", views.AppViewSet, basename="app")

urlpatterns = [
    # API 路由
    path("", include(router.urls)),
]
