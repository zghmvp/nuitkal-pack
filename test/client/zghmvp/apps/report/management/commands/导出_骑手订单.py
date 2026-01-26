# user-hongsongjie user-lianda
import calendar
from datetime import datetime, timedelta
from typing import cast

import pandas
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand

from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.browser import AsyncBrowserManager, async_browser_manage_func_run
from zghmvp.apps.report.tools.kanban import 看板
from zghmvp.apps.report.tools.log import PrintBlock, print_command_and_args
from zghmvp.config import BROWSER_CDP_看板
from zghmvp.tools.format import parse_date
from zghmvp.tools_old.fmt import format_site_info
from zghmvp.tools_old.pd import ExcelWriterManager


class Command(BaseCommand):
    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--date", type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--date-range", nargs=2, type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--now", action="store_true", default=False, help="导出实时订单")
        group.add_argument("--auto", action="store_true", default=False, help="自动判断导出半月还是一整个月")
        group.add_argument("--month", action="store_true", default=False, help="一整个月")

    def handle(self, *args, **kwargs):
        print_command_and_args(__file__, kwargs)

        if kwargs.get("date_range"):
            start_date, end_date = kwargs["date_range"]

        elif kwargs["now"]:
            start_date = end_date = datetime.now().date()

            @async_browser_manage_func_run(BROWSER_CDP_看板)
            async def _(manager: AsyncBrowserManager):
                boot看板 = 看板(manager)
                await boot看板.看板_订单(start_date, end_date)

        elif kwargs["month"]:
            end_date = datetime.now().date() - timedelta(days=1)
            start_date = end_date.replace(day=1)

        elif kwargs["auto"]:
            end_date = datetime.now().date() - timedelta(days=1)
            if end_date.day < 15:
                end_date = end_date - relativedelta(months=1)
                end_date = end_date.replace(day=calendar.monthrange(end_date.year, end_date.month)[-1])
                start_date = end_date.replace(day=1)
            else:
                end_date = end_date.replace(day=15)
                start_date = end_date.replace(day=1)

        elif kwargs.get("date"):
            start_date = end_date = kwargs["date"]

        else:
            end_date = datetime.now().date() - timedelta(days=1)
            start_date = end_date.replace(day=1)

        with PrintBlock("导出-骑手订单 {} ~ {}".format(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))) as p:
            with p.print_inline_env("读取骑手数据"):
                df_骑手订单 = pandas.DataFrame(
                    report_models.看板_订单_骑手.objects.filter(日期__gte=start_date, 日期__lte=end_date).values(
                        "站点ID",
                        "日期",
                        "骑手姓名",
                        "骑手mis号",
                        "骑手ID",
                        "是否大网骑手",
                        "推配单量",
                        "接单量",
                        "推配完成单量",
                        "完成单量",
                        "夜配完成单量",
                        "高峰期完成单量",
                        "午高峰完成单量",
                        "晚高峰完成单量",
                        "全天单量是否达成",
                        "午高峰单量是否达成",
                        "晚高峰单量是否达成",
                        "高峰期单量是否达成",
                        "有效运力是否达成",
                        "超时单量",
                    )
                )

            with p.print_inline_env("读取站点数据"):
                df_站点订单 = pandas.DataFrame(
                    report_models.看板_订单_站点.objects.filter(日期__gte=start_date, 日期__lte=end_date).values(
                        "站点ID",
                        "日期",
                        "大网单量",
                        "推配完成单量",
                        "完成单量",
                        "夜配完成单量",
                        "月累计完成单量",
                        "月工作日天数",
                        "月非工作日天数",
                        "月工作日完成单量",
                        "月工作日日均单量",
                        "月非工作日完成单量",
                        "月非工作日日均单量",
                        "月预估单量",
                        "跑单骑手",
                        "出勤骑手",
                        "有单骑手",
                        "人效骑手",
                        "人效",
                        "有效运力达成骑手数",
                        "运力目标",
                        "运力考核",
                        "出勤未达成",
                        "运力达成率",
                        "运力满足率",
                        "运力缺口",
                        "运力达成差值",
                        "出勤未达成数",
                        "全天单量未达成骑手数",
                        "午高峰单量未达成骑手数",
                        "晚高峰单量未达成骑手数",
                        "高峰期单量未达成骑手数",
                        "超时单量",
                    )
                )

            with p.print_inline_env("读取骑手月汇总数据"):
                df_骑手订单_月汇总 = df_骑手订单.groupby(["站点ID", "骑手姓名", "骑手mis号", "是否大网骑手"], as_index=False)[
                    ["接单量", "推配完成单量", "完成单量", "高峰期完成单量", "午高峰完成单量", "晚高峰完成单量", "超时单量"]
                ].sum()

            df_站点订单_月汇总 = df_站点订单.copy().sort_values("日期")
            df_站点订单_月汇总["日期"] = pandas.to_datetime(df_站点订单_月汇总.日期).dt.month
            df_站点订单_月汇总 = df_站点订单_月汇总.groupby(["站点ID", "日期"], as_index=False).agg(
                {
                    "大网单量": "sum",
                    "推配完成单量": "sum",
                    "完成单量": "sum",
                    "夜配完成单量": "sum",
                    "月工作日天数": "last",
                    "月非工作日天数": "last",
                    "月工作日完成单量": "last",
                    "月工作日日均单量": "last",
                    "月非工作日完成单量": "last",
                    "月非工作日日均单量": "last",
                    "月预估单量": "last",
                    "跑单骑手": "sum",
                    "出勤骑手": "sum",
                    "有单骑手": "sum",
                    "人效骑手": "sum",
                    "人效": "sum",
                    "有效运力达成骑手数": "sum",
                    "运力目标": "sum",
                    "运力考核": "sum",
                    "出勤未达成": "sum",
                    "运力达成率": "sum",
                    "运力满足率": "sum",
                    "运力缺口": "sum",
                    "运力达成差值": "sum",
                    "出勤未达成数": "sum",
                    "全天单量未达成骑手数": "sum",
                    "午高峰单量未达成骑手数": "sum",
                    "晚高峰单量未达成骑手数": "sum",
                    "高峰期单量未达成骑手数": "sum",
                    "超时单量": "sum",
                }
            )
            df_站点订单_月汇总["运力满足率"] = df_站点订单_月汇总.出勤骑手.div(df_站点订单_月汇总.运力目标)
            df_站点订单_月汇总["运力达成率"] = df_站点订单_月汇总.运力考核.div(df_站点订单_月汇总.运力目标)
            df_站点订单_月汇总["人效"] = df_站点订单_月汇总["完成单量"] / df_站点订单_月汇总["出勤骑手"]

            with ExcelWriterManager(data_date=cast(datetime, end_date), file_name="骑手订单 {} ~ {}.xlsx".format(start_date.strftime("%Y-%m-%d"), end_date.day)) as writer:
                df_骑手订单 = format_site_info(df_骑手订单, city_name=True, areal_name=True, site_name=True, site_id=True, default_site_id_column="站点ID")
                df_骑手订单_月汇总 = format_site_info(df_骑手订单_月汇总, city_name=True, areal_name=True, site_name=True, site_id=True, default_site_id_column="站点ID")
                df_站点订单 = format_site_info(df_站点订单, city_name=True, areal_name=True, site_name=True, site_id=True, default_site_id_column="站点ID")
                df_站点订单_月汇总 = format_site_info(df_站点订单_月汇总, city_name=True, areal_name=True, site_name=True, site_id=True, default_site_id_column="站点ID")

                writer.to_excel(df_骑手订单, sheet_name="骑手", index=False)
                writer.to_excel(df_骑手订单_月汇总, sheet_name="骑手月汇总", index=False)
                writer.to_excel(df_站点订单, sheet_name="站点", index=False)
                writer.to_excel(df_站点订单_月汇总, sheet_name="站点月汇总", index=False)
