# core
import importlib
import importlib.util
from datetime import date, datetime
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

import polars

from zghmvp.apps.base import models as base_models
from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.数据工具.考核工具 import get_site_parent_tree
from zghmvp.tools import typed_cache
from zghmvp.tools.system import get_dir_modules

if TYPE_CHECKING:
    from zghmvp.apps.report.tools.播报.p202601.base import Base考核方式

get_dir_modules(Path(__file__).parent)


def _rank_items(items: list[report_models.日播报]) -> None:
    for rank, item in enumerate(sorted(items, key=lambda x: dict(x.数据)["达成_得分"], reverse=True), start=1):
        data = dict(item.数据)
        rank_key = "达成_排名"
        if rank_key not in data:
            raise ValueError("达成_得分不存在")
        data[rank_key] = rank

        item.数据 = list(data.items())
        item.save()


@typed_cache
def get_city_module(city_name: str) -> ModuleType:
    package_name = f"{__package__}.{city_name}"
    return importlib.import_module(package_name)


@typed_cache
def get_areal_module(areal_name: str) -> ModuleType:
    areal = base_models.区域.objects.select_related("城市").filter(区域名称=areal_name).get()
    return get_city_module(areal.城市.城市名称)


@typed_cache
def get_site_module(site_name: str) -> ModuleType:
    site = base_models.站点.objects.select_related("城市").filter(站点名称=site_name).get()
    package_name = f"{__package__}.{site.城市.城市名称}.{site.站点名称}"

    if importlib.util.find_spec(package_name):
        return importlib.import_module(package_name)

    return get_city_module(site.城市.城市名称)


@typed_cache
def 日播报(data_date: date) -> None:
    city_rank: list[report_models.日播报] = []
    areal_rank: list[report_models.日播报] = []
    for city in base_models.城市.select_enable(data_date):
        city_module = get_city_module(city.城市名称)

        site_rank: list[report_models.日播报] = []
        for areal in base_models.区域.select_enable(data_date).filter(城市=city).all():
            areal_module = get_areal_module(areal.区域名称)

            for site in base_models.站点.select_enable(data_date).filter(区域=areal).all():
                site_module = get_site_module(site.站点名称)
                site_播报 = site_module.站点日播报(data_date, site)
                site_rank.append(site_播报.读取数据与计算())

            areal_播报 = areal_module.区域日播报(data_date, areal)
            areal_rank.append(areal_播报.读取数据与计算())
        _rank_items(site_rank)  # 站点排名

        city_播报 = city_module.城市日播报(data_date, city)
        city_播报.读取数据与计算()
        city_rank.append(city_播报.读取数据与计算())

    _rank_items(areal_rank)  # 区域排名
    _rank_items(city_rank)  # 城市排名

    first_city = base_models.城市.select_enable(data_date).first()
    root = get_city_module(first_city.城市名称).商日播报(data_date)  # type: ignore
    root.读取数据与计算()


@typed_cache
def 月播报(data_date: date):
    results = []
    for site in base_models.站点.select_enable(data_date).all():
        site_module = get_site_module(site.站点名称)
        site_播报 = site_module.站点月播报(data_date, site)
        results.append(site_播报.读取数据与计算())

    pl_main = polars.DataFrame(results)
    # 按城市ID分组，根据城市，比较"达成_得分"各自从1开始按顺序排名
    pl_main = pl_main.with_columns(
        polars.col("达成_得分").rank(method="min", descending=True).over("城市ID").alias("达成_排名"),
    )
    return pl_main


@typed_cache
def 考核方式(
    data_date: date,
    city_name: Any = None,
    city_id: Any = None,
    areal_name: Any = None,
    areal_id: Any = None,
    site_name: Any = None,
    site_id: Any = None,
) -> "Base考核方式":
    city, areal, site = get_site_parent_tree(
        city_name=city_name,
        city_id=city_id,
        areal_name=areal_name,
        areal_id=areal_id,
        site_name=site_name,
        site_id=site_id,
    )

    if site_name or site_id:
        module = get_site_module(site.站点名称)
    elif areal_name or areal_id:
        module = get_areal_module(areal.区域名称)
    elif city_name or city_id:
        module = get_city_module(city.城市名称)
    else:
        raise ValueError("请提供站点、区域或城市名称或ID")

    return module.考核方式(data_date=data_date)
