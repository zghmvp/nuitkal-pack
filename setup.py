from setuptools import find_packages, setup

install_requires = []  # 没有通用依赖

# 定义可选依赖组
extras_require = {
    "server": [
        "Django>=4.2",
        "djangorestframework>=3.14",
    ],
    "client": [
        "requests>=2.32.3",
        "diskcache>=5.6.3",
        "pathspec>=1.0.3",
        "nuitka>=2.8.9",
    ],
}

# 可选：提供一个 'all' 组，包含所有依赖
extras_require["all"] = extras_require["server"] + extras_require["client"]

setup(
    name="nuitkal-pack",
    version="1.0.0",
    author="ZGHMVP",
    description="客户端版本更新和自动分发系统",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
