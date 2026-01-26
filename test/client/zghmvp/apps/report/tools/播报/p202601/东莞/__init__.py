# user-hongsongjie
import statistics
from datetime import date, datetime
from pathlib import Path

from chinese_calendar import is_workday

from zghmvp.apps.base import models as base_models
from zghmvp.apps.report.tools.播报.p202601.base import Base公式计算, Base区域日播报, Base商日播报, Base城市日播报, Base站点日播报, Base站点月播报, Base考核方式
from zghmvp.tools import is_workday_cache
from zghmvp.tools.format import auto_datetime_convert, parse_time_range

package_path = Path(__file__).parent
package_name: str = package_path.stem
city: base_models.城市 = base_models.城市.objects.get(城市名称=package_name)


class 考核方式(Base考核方式):
    @auto_datetime_convert
    def __init__(self, data_date: datetime | date) -> None:
        super().__init__(data_date)

    def 核心考核方案(self) -> dict:
        """
        # vscode 保留列顺序：考核项 分值 0分值(255,0,0) 80分值(255,122,122) 100分值(255,199,206)
        # vscode 正则1：(.+?)\t(.+?)\t(.+?)\t(.+?)\t(.+)
        # vscode 正则2："$1": {"分数": $2, "0": $3, "80": $4, "100": $5},
        """

        def 自动计算中间值(data: dict):
            if data["0"] is not None and data["100"] is not None and data["80"] is None:
                data["80"] = statistics.median([data["0"], data["100"]])
            return data

        城市维度方案 = self.get_config_by_day(
            self.data_date,
            {
                "default": {
                    "配送准时率": {"分数": 20, "0": 0.880000, "80": 0.935000, "100": 0.967500},
                    "复合严重超时率": 自动计算中间值({"分数": 20, "0": 0.020000, "80": None, "100": 0.010000}),
                    "配送客诉率": {"分数": 15, "0": 0.000900, "80": 0.000730, "100": 0.000550},
                    "虚假点送达": {"分数": 10, "0": 0.003500, "80": 0.002600, "100": 0.002100},
                    "骑手装备不合格率": {"分数": 5, "0": 0.021000, "80": 0.013000, "100": 0.004500},
                    "有效运力达成率": {"分数": 30, "0": 0.850000, "80": 0.950000, "100": 1.000000},
                    "安全管理": {"分数": [-10, 0], "0": None, "80": None, "100": None},
                    "配送原因取消订单占比": {"分数": [-10, 0], "0": None, "80": None, "100": 0.001200},
                    "精细化排班": {"分数": [-3, 3], "0": None, "80": None, "100": None},
                    "箱贴不合格": {"分数": [-2, 0], "0": None, "80": None, "100": 2.000000},
                    "有效运力达成率（新站开业首日和次日）": {"分数": [-5, 0], "0": None, "80": None, "100": 1.000000},
                    "骑手行为异常率": {"分数": [-5, 5], "0": 0.000340, "80": 0.000220, "100": 0.000200},
                    "严重行为客诉率": {"分数": [-3, 2], "0": 0.000060, "80": 0.000034, "100": 0.000025},
                    "准时达标站日次": {"分数": [-5, 0], "0": None, "80": None, "100": 0.930000},
                    "夜班时段准时达标站日次": {"分数": [-2, 0], "0": None, "80": None, "100": None},
                },
                # (24, 30): {
                #     "配送准时率": {"分数": 25, "0": 0.880000, "80": 0.930000, "100": 0.957000},
                #     "复合严重超时率": {"分数": 10, "0": 0.025000, "80": None, "100": 0.013200},
                #     "配送客诉率": {"分数": 15, "0": 0.001180, "80": 0.000930, "100": 0.000680},
                #     "虚假点送达": {"分数": 10, "0": 0.004900, "80": 0.003700, "100": 0.002800},
                # },
            },
        )
        return 城市维度方案

    def 运力考核方案(self) -> dict:
        r"""
        粘贴格式：
            深圳 工作日 ≥25 ≥10 ≥0 ≥10 [09:00-12:00） [16:00-22:00）
            深圳 非工作日 ≥25 ≥15 ≥0 ≥0 [09:00-12:00） [16:00-20:00）

        正则：(.+?)\s(.+?)\s≥(.+?)\s≥(.+?)\s≥(.+?)\s≥(.+?)\s(.+?)\s(.+)
        值："$2":{\n"完成单量目标-全天":$3,"完成单量目标-高峰":$4,"完成单量目标-午高峰":$5,"完成单量目标-晚高峰":$6,\n"时段-午高峰":parse_time_range("$7"),"时段-晚高峰":parse_time_range("$8"),\n},
        """
        城市维度方案 = {
            "is_workday": is_workday,
            "工作日": {
                "完成单量目标-全天": 25,
                "完成单量目标-高峰": 15,
                "完成单量目标-午高峰": 0,
                "完成单量目标-晚高峰": 0,
                "时段-午高峰": parse_time_range("[10:00-12:00）"),
                "时段-晚高峰": parse_time_range("[16:00-22:00）"),
            },
            "非工作日": {
                "完成单量目标-全天": 25,
                "完成单量目标-高峰": 15,
                "完成单量目标-午高峰": 3,
                "完成单量目标-晚高峰": 0,
                "时段-午高峰": parse_time_range("[09:00-12:00）"),
                "时段-晚高峰": parse_time_range("[16:00-21:00）"),
            },
        }
        return 城市维度方案


class 公式计算(Base公式计算):
    pass


class 站点日播报(公式计算, Base站点日播报):
    考核方式 = 考核方式


class 区域日播报(公式计算, Base区域日播报):
    考核方式 = 考核方式


class 城市日播报(公式计算, Base城市日播报):
    考核方式 = 考核方式


class 商日播报(公式计算, Base商日播报):
    考核方式 = 考核方式


class 站点月播报(公式计算, Base站点月播报):
    考核方式 = 考核方式
