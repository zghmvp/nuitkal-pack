# user-hongsongjie
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import cast

import pandas
from django.core.management.base import BaseCommand

from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.excel import ExcelTemplateScreenshot
from zghmvp.apps.report.tools.kanban import 考核工具
from zghmvp.apps.report.tools.log import print_command_and_args
from zghmvp.apps.report.tools.播报.p202601 import 月播报
from zghmvp.tools.format import parse_date
from zghmvp.tools_old.fmt import format_cityareal_info, format_site_info
from zghmvp.tools_old.pd import ExcelWriterManager


class Command(BaseCommand):
    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--date", type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--date-range", nargs=2, type=parse_date, help="日期，格式：YYYY-MM-DD")

    def handle(self, *args, **kwargs):
        print_command_and_args(__file__, kwargs)

        if kwargs.get("date_range"):
            start_date, end_date = kwargs["date_range"]

        elif kwargs.get("date"):
            end_date = start_date = cast(date, kwargs["date"])

        else:
            end_date = datetime.now().date() - timedelta(days=1)
            if report_models.日播报.objects.exists() is False:
                start_date = end_date
            else:
                start_date = report_models.日播报.objects.order_by("日期").last().日期 + timedelta(days=1)
                start_date = min(start_date, end_date)

        for data_date in pandas.date_range(start_date, end_date):
            print(data_date)
            考核工具.日播报(data_date)

            query_data = defaultdict(list)
            for item in report_models.日播报.objects.filter(日期=data_date):
                query_data[item.类型].append(
                    {
                        "日期": item.日期,
                        "城市ID": item.城市ID,
                        "区域ID": item.区域ID,
                        "站点ID": item.站点ID,
                        **dict(item.数据),
                    }
                )

            # 读取播报数据
            df_query_data: dict[str, pandas.DataFrame] = {}
            with ExcelWriterManager(data_date=data_date, sub_dir="日数据播报", file_name="日-播报 {date}.xlsx") as excel_manager:
                for data_type, data in query_data.items():
                    df = pandas.DataFrame(data).sort_values(by=["达成_得分"], ascending=False)

                    if data_type == "站点":
                        format_site_info(df, city_name=True, areal_name=True, site_name=True, default_site_id_column=True, partner_name=True, inplace=True)
                        df_query_data[data_type] = df.copy()

                    else:
                        format_cityareal_info(df, city_name=True, areal_name=True, partner_name=True, inplace=True)
                        df_query_data[data_type] = df.copy()

                        for column, insert_name in (
                            ("商", "城市"),
                            ("城市", "区域"),
                            ("区域", "站点名称"),
                        ):
                            if insert_name not in df_query_data[data_type].columns:
                                df_query_data[data_type].insert(df_query_data[data_type].columns.get_loc(column) + 1, insert_name, None)

                    # 输出到文件，供调试使用
                    df.columns = pandas.MultiIndex.from_tuples(((column, "") if "_" not in column else column.split("_") for column in df.columns))
                    excel_manager.to_excel(df, sheet_name=data_type)

            from zghmvp.apps.report.tools.format import format_site_info as format_site_info_polars

            pl_main = 月播报(data_date)
            pl_main = format_site_info_polars(pl_main, city_name=True, areal_name=True, site_name=True, default_site_id_column=True)

            with ExcelTemplateScreenshot("日数据播报.xlsx") as manager:
                for (city_name,), pl_city in pl_main.group_by("城市名称"):
                    考核方式 = 考核工具.获取_考核方式(data_date=data_date)(data_date=data_date, city_name=city_name)

                    excel_config = 考核方式.核心考核方案_转Excel配置()
                    manager.fill_city_config(city_name, excel_config)

                    manager.append_value(pl_city, sheet="站点-月")
                save_path = manager.save_to(data_date=data_date, sub_dir="日数据播报", file_name="月-播报 {date}.xlsx", sheet_names=["配置", "站点-月"])
                print(save_path)
