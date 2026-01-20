from typing import TypedDict


class FileInfo(TypedDict):
    """统一的文件信息类型定义

    所有文件操作（add、keep、delete）都使用这个统一的结构
    确保数据类型的一致性和处理的统一性
    """

    hash: str  # 文件哈希值
    path: str  # 文件路径
    url: str  # 下载路径
    size: int  # 文件大小（字节），不需要时为 0


class IncrementalUpdateInfo(TypedDict):
    """增量更新信息类型定义

    描述增量更新过程中所有文件的变更信息
    所有字段都使用统一的 FileInfo 类型
    """

    add: list[FileInfo]  # 需要添加的文件
    keep: list[FileInfo]  # 可以保留的文件
    delete: list[FileInfo]  # 需要删除的文件
