# core
from django.core.management.base import BaseCommand

from zghmvp.apps.report.tools.browser import AsyncBrowserManager, async_browser_manage_func_run
from zghmvp.apps.report.tools.dengta import 灯塔
from zghmvp.apps.report.tools.log import PrintLineStatus, print_command_and_args
from zghmvp.apps.report.tools.path import get_date_data_dir
from zghmvp.apps.report.tools.数据工具.核心数据解析 import 核心数据解析
from zghmvp.config import BROWSER_CDP_灯塔
from zghmvp.tools.input import wait_input_zip_file_path


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        print_command_and_args(__file__, kwargs)

        zip_path = wait_input_zip_file_path("请输入核心数据zip文件路径：")

        @async_browser_manage_func_run(BROWSER_CDP_灯塔)
        async def _(manager: AsyncBrowserManager):
            async with 核心数据解析(zip_path) as zip:
                boot灯塔 = 灯塔(manager)
                for data_date in zip.data_dates:
                    await zip.灯塔_下载缺失文件(boot灯塔, data_date)

                    results_list = [
                        await zip.格式化_核心数据(data_date),
                        await zip.格式化_配送原因取消明细(data_date),
                        await zip.格式化_配送超时明细(data_date),
                        await zip.格式化_排班数据汇总(data_date),
                        await zip.格式化_骑手出勤明细(data_date),
                        await zip.格式化_策略触发明细(data_date),
                        await zip.格式化_骑手进站分拣明细(data_date),
                        await zip.格式化_不合格订单明细(data_date),
                        await zip.格式化_客诉明细(data_date),
                    ]

                    zip_files = {name: df for name, df, _ in results_list if df is not None}

                    zip.save_to(get_date_data_dir(data_date, file_name="核心数据-parquet.zip"), results=zip_files, save_type=".parquet")
                    zip.save_to(get_date_data_dir(data_date, file_name="核心数据-csv.zip"), results=zip_files, save_type=".csv")

                    for name, df, db_dave in results_list:
                        with PrintLineStatus(name):
                            db_dave()
