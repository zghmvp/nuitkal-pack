# user-hongsongjie
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from zghmvp.apps.base import models as base_models
from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.browser import AsyncBrowserManager, async_browser_manage_func_run
from zghmvp.apps.report.tools.dengta import 灯塔
from zghmvp.apps.report.tools.kanban import 看板
from zghmvp.apps.report.tools.log import print_command_and_args
from zghmvp.config import BROWSER_CDP_看板
from zghmvp.tools.format import parse_date


class Command(BaseCommand):
    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--date", type=parse_date, help="日期，格式：YYYY-MM-DD")
        group.add_argument("--date-range", nargs=2, type=parse_date, help="日期，格式：YYYY-MM-DD")

    def handle(self, *args, **kwargs):
        print_command_and_args(__file__, kwargs)

        if kwargs.get("date_range"):
            start_date, end_date = kwargs["date_range"]
        else:
            start_date = kwargs.get("date")
            if not start_date:
                start_date = datetime.now().date() - timedelta(days=1)

                for d in range(1, 10):  # 循环往回检查最多十天
                    pre_date = start_date - timedelta(days=d)
                    sites = base_models.站点.select_enable(pre_date).all()  # 这一天未停用的站点
                    if report_models.看板_订单_站点.objects.filter(日期=pre_date, 站点__in=sites).count() != len(sites):  # 查询站点数据与订单条数是否一致
                        start_date = pre_date
                    else:
                        break

            end_date = start_date

        @async_browser_manage_func_run(BROWSER_CDP_看板)
        async def _(manager: AsyncBrowserManager):
            boot看板 = 看板(manager)
            boot灯塔 = 灯塔(manager)

            await boot灯塔.考核奖惩_站点运力考核目标(start_date, end_date)
            await boot看板.看板_订单(start_date, end_date)

        from django.core.management import call_command

        call_command("导出_骑手单量汇总", "--date-range", start_date, end_date)
        call_command("导出_骑手订单", "--month")
