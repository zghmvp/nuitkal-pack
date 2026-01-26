# core
import polars
from django.core.management.base import BaseCommand

from zghmvp.apps.base import models as base_models
from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.format import format_site_info
from zghmvp.tools.input import wait_input_excel_file_path


def save_todb(pl_main: polars.DataFrame):
    for row in pl_main.iter_rows(named=True):
        obj = report_models.站点配置.objects.filter(站点ID=row["站点ID"], 日期=row["日期"], 站点难度=row["站点难度"]).first()
        if not obj:
            obj = report_models.站点配置(城市ID=row["城市ID"], 区域ID=row["区域ID"], 站点ID=row["站点ID"], 日期=row["日期"], 站点难度=row["站点难度"])

        for key in ["目标线", "安全线"]:
            if row.get(key, None) is not None:
                setattr(obj, key, row[key])
        obj.save()


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        path = wait_input_excel_file_path("请输入配置文件(Excel)路径：")

        df_site = polars.read_excel(path, sheet_name="目标线安全线")
        if df_site.is_empty():
            raise ValueError("站点配置不能为空")

        pl_site = format_site_info(df_site, city_id=True, areal_id=True, site_id=True, default_site_name_column="站点名称")

        # 删除旧数据
        for row in pl_site.select(["站点ID", "日期"]).unique().iter_rows(named=True):
            report_models.站点配置.objects.filter(站点ID=row["站点ID"], 日期=row["日期"]).delete()

        # 新增
        for row in pl_site.iter_rows(named=True):
            site = base_models.站点.objects.get(站点ID=row["站点ID"])
            obj = report_models.站点配置.objects.create(
                城市ID=site.城市ID,
                区域ID=site.区域ID,
                站点ID=site.id,
                日期=row["日期"],
                站点难度=row["站点难度"],
                督导=row["督导"],
                目标线=row["目标线"],
                安全线=row["安全线"],
            )
            print("+ 站点配置信息添加成功：{}".format(obj))
