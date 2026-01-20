import hashlib


def calculate_file_hash(content: bytes) -> str:
    """计算文件内容的 SHA256 哈希值

    Args:
        content: 文件二进制内容

    Returns:
        64位十六进制哈希字符串

    Examples:
        >>> content = b"Hello, World!"
        >>> hash_value = calculate_file_hash(content)
        >>> len(hash_value)
        64

    """
    return hashlib.sha256(content).hexdigest()
