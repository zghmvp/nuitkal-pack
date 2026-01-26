# core
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import BooleanField, Case, Count, F, IntegerField, Value, When

from zghmvp.apps.report import models as report_models
from zghmvp.apps.report.tools.browser import AsyncBrowserManager, async_browser_manage_func_run
from zghmvp.apps.report.tools.dengta import 灯塔
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
            today = datetime.now().date()

            if not start_date:
                # ========== 判断今天到前5天是否有大量站点未更新运力目标 ========== #
                temp = (
                    report_models.灯塔_考核奖惩_站点运力考核目标.objects.filter(日期__gte=today - timedelta(days=5), 日期__lte=today)
                    .values("日期")
                    .annotate(  # 计算每天的站点数量以及无运力目标的站点数量
                        站点数量=Count("站点ID", distinct=True),
                        无运力目标站点=Count(Case(When(运力目标=-1, then=1), output_field=IntegerField())),
                    )
                    .annotate(  # 然后判断是否超过阈值（1/4），判断该天是否有遗漏未更新的站点
                        超过阈值=Case(
                            When(无运力目标站点__gt=F("站点数量") / 4, then=Value(True)),
                            default=Value(False),
                            output_field=BooleanField(),
                        )
                    )
                    .filter(超过阈值=True)
                    .order_by("日期")
                    .first()
                )

                # 如果没有就用今天作为起始时间
                start_date = temp["日期"] if temp else today

                # 结束时间固定为今天+3天
                end_date = today + timedelta(days=3)
            else:
                end_date = start_date

        @async_browser_manage_func_run(BROWSER_CDP_看板)
        async def _(manager: AsyncBrowserManager):
            boot灯塔 = 灯塔(manager)
            await boot灯塔.考核奖惩_站点运力考核目标(start_date, end_date)
