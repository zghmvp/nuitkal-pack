# user-hongsongjie user-lianda
from datetime import date, datetime, timedelta

import pandas
from django.core.management.base import BaseCommand

from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.boot import DingtalkAuto
from zghmvp.apps.report.tools.log import print_command_and_args
from zghmvp.apps.report.tools.数据工具.考核工具 import 考核工具
from zghmvp.tools.format import auto_datetime_convert, parse_date
from zghmvp.tools_old.fmt import format_site_info
from zghmvp.tools_old.pd import ExcelWriterManager


@auto_datetime_convert
def 骑手单量汇总(start_date: date, end_date: date, df: pandas.DataFrame = None, default_site_id_column: bool | str | None = None, default_site_name_column: str | None = None):
    if df is None:
        df = pandas.DataFrame(report_models.看板_订单_骑手.objects.filter(日期__gte=start_date, 日期__lte=end_date).values())

    if default_site_id_column is not None or default_site_name_column is not None:
        format_site_info(
            df,
            city_name=True,
            areal_name=True,
            site_name=True,
            default_site_id_column=default_site_id_column,
            default_site_name_column=default_site_name_column,
            inplace=True,
        )

    columns_name = [
        "日期",
        "骑手姓名",
        "骑手ID",
        "已完成",
        "待揽收",
        "配送中",
        "超时",
        "预约单提前送达",
        "取消",
        "平均配送总时长（分）",
        "平均揽收时长（分）",
        "平均配送时长（分）",
        "累计工作时长(小时)",
        "站点",
        "城市",
        "接单量",
        "区域",
        "周中周末",
        "工作周",
        "是否大网骑手",
    ]
    df = df.rename(columns={"推配完成单量": "已完成", "超时单量": "超时", "站点名称": "站点"}).reindex(columns=columns_name)
    df["工作周"] = pandas.to_datetime(df.日期).map(考核工具.获取_工作周)
    df["周中周末"] = df.apply(lambda x: 考核工具.获取_考核方式(x.日期)(x.日期, site_name=x.站点).是否工作日(to_str=True), axis=1)
    return df


class Command(BaseCommand):
    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--date", type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--date-range", nargs=2, type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--auto", action="store_true", default=False, help="自动判断导出半月还是一整个月")
        group.add_argument("--month", action="store_true", default=False, help="一整个月")
        group.add_argument("--send", action="store_true", default=False, help="一整个月")

    def handle(self, *args, **kwargs):
        print_command_and_args(__file__, kwargs)

        if kwargs.get("date_range"):
            start_date, end_date = kwargs["date_range"]

        elif kwargs["month"]:
            end_date = datetime.now().date() - timedelta(days=1)
            start_date = end_date.replace(day=1)

        elif kwargs.get("date"):
            start_date = end_date = kwargs.get("date")

        else:
            start_date = end_date = datetime.now().date() - timedelta(days=1)

        with ExcelWriterManager(end_date, file_name="单量汇总 {} ~ {}.xlsx".format(start_date.strftime("%Y-%m-%d"), end_date.day)) as writer:
            df = 骑手单量汇总(start_date, end_date, default_site_id_column=True)
            writer.to_excel(df, index=False)

        if kwargs["send"]:
            with DingtalkAuto() as boot:
                boot.send_msg("数据接收群", files=[writer.path])
