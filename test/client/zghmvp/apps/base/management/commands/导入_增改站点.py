# core
import re
from datetime import datetime

import polars
from django.core.management.base import BaseCommand

from zghmvp.apps.base import models as base_models
from zghmvp.tools.input import wait_input_excel_file_path


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = wait_input_excel_file_path()

        pl_config = polars.read_excel(path, sheet_name="配置")
        df_city = pl_config.select(["城市", "城市ID"]).drop_nulls()
        df_areal = pl_config.select(["区域", "区域ID"]).drop_nulls()

        for city_info in df_city.iter_rows(named=True):
            city, _ = base_models.城市.objects.get_or_create(id=city_info["城市ID"], defaults={"城市名称": city_info["城市"], "启用时间": datetime.now().date()})

            for areal_name in pl_config[city_info["城市"]].drop_nulls():
                areal_id = df_areal.filter(polars.col("区域") == areal_name)["区域ID"].item()
                areal, _ = base_models.区域.objects.get_or_create(id=areal_id, defaults={"城市": city, "区域名称": areal_name, "启用时间": datetime.now().date()})

        df = polars.read_excel(path, sheet_name="站点增改")

        for row in df.to_dicts():
            city = base_models.城市.objects.get(城市名称=row["城市"])
            areal = base_models.区域.objects.get(区域名称=row["区域"])

            site, status = base_models.站点.objects.update_or_create(
                城市=city,
                区域=areal,
                id=row["站点ID"],
                defaults={
                    "站点名称": re.search("-(.+?)-", row["站点名称"]).group(1),  # type: ignore
                    "站点全称": row["站点名称"],
                    "启用时间": row["启用时间"],
                    "停用时间": row["停用时间"],
                },
            )
            if status:
                print("+ 站点添加成功：{}".format(site.站点名称))
            else:
                print("* 站点修改成功：{}".format(site.站点名称))
