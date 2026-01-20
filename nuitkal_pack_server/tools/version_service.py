from typing import TYPE_CHECKING, Optional, Union

from nuitkal_pack_server.models import App, AppVersion, VersionFile
from nuitkal_pack_server.tools.hash_utils import calculate_file_hash

if TYPE_CHECKING:
    from django.core.files.base import ContentFile
    from django.core.files.uploadedfile import UploadedFile


if TYPE_CHECKING:
    from .types import IncrementalUpdateInfo


class VersionService:
    """版本管理服务类

    提供版本相关的核心业务逻辑
    """

    @staticmethod
    def upload_file(file: Union["UploadedFile", "ContentFile"]) -> VersionFile:
        """上传单个文件"""
        hash_id = calculate_file_hash(file.read())
        name = file.name

        obj = VersionFile.objects.filter(id=hash_id).first()
        if obj:
            return obj

        obj = VersionFile(id=hash_id, name=name, size=file.size, file=file)
        obj.save()
        return obj

    @staticmethod
    def create_version(app: App, *, version: str, entry_point: str, file_manifest: dict[str, str], changelog: str = "", is_active: bool = False) -> AppVersion:
        """创建新版本

        Args:
            app: 应用对象
            version: 版本号
            entry_point: 入口文件路径
            file_manifest: 文件清单
            changelog: 更新日志
            is_active: 是否激活

        Returns:
            创建的版本对象

        Raises:
            ValueError: 版本已存在

        """
        # 检查版本唯一性
        if AppVersion.objects.filter(app=app, version=version).exists():
            raise ValueError(f"版本 {version} 已存在")

        files = VersionFile.objects.filter(id__in=file_manifest.values()).values_list("id", flat=True)
        not_exist_files = set(file_manifest.values()) - set(files)
        if not_exist_files:
            raise ValueError(f"未上传的文件列表, 请上传完毕后再创建新版本: {'、'.join(not_exist_files)}")

        return AppVersion.objects.create(
            app=app,
            version=version,
            entry_point=entry_point,
            changelog=changelog,
            file_manifest=file_manifest,
            is_active=is_active,
        )

    @staticmethod
    def get_update_info(app: App, current_version: Optional[str]) -> Union[dict, "IncrementalUpdateInfo"]:
        """获取更新信息，传入版本号是增量更新，为空是全量更新

        Args:
            app: 应用对象
            current_version: 当前版本号（可选）

        Returns:
            更新信息字典，包含:
            - need_update: 是否需要更新
            - current_version: 当前的版本
            - active_version: 激活的版本
            - add: 需要添加的文件列表
            - keep: 可以保留的文件列表
            - delete: 需要删除的文件列表
            - entry_point: 程序入口
            - changelog: 更新日志

        Raises:
            ValueError: 应用无激活版本或本地版本不存在

        """
        active_version = app.get_active_version()
        if not active_version:
            raise ValueError("该应用暂无激活版本")

        local_version = app.appversion_set.filter(version=current_version).first()

        result = {
            "current_version": current_version or None,
            "active_version": active_version.version,
            "entry_point": active_version.entry_point,
            "changelog": active_version.changelog,
            "need_update": True,
        }
        if local_version:
            if current_version == active_version.version:
                result["need_update"] = False

            local_manifest = local_version.file_manifest
        else:
            local_manifest = {}

        # 计算需要更新的文件
        update_info = active_version.get_all_core_files(local_manifest)

        return dict(
            result,
            **update_info,
        )
