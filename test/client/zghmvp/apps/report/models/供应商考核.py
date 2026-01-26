# core
from django.db import models

from .base import DateBaseModel


class KPI达成(DateBaseModel):
    站点难度 = models.CharField(max_length=16)
    分级 = models.CharField(max_length=16)
    配送准时率 = models.FloatField()
    配送准时率_得分 = models.FloatField()
    复合严重超时率 = models.FloatField()
    复合严重超时率_得分 = models.FloatField()
    配送客诉率 = models.FloatField()
    配送客诉率_得分 = models.FloatField()
    虚假点送达率 = models.FloatField()
    虚假点送达率_得分 = models.FloatField()
    有效运力达成率 = models.FloatField()
    有效运力达成率_得分 = models.FloatField()
    装备不合规率 = models.FloatField()
    装备不合规率_得分 = models.FloatField()
    取消单扣分 = models.FloatField()

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("日期", "站点"),)


class 站点配置(DateBaseModel):
    督导 = models.CharField(max_length=16)
    站点难度 = models.CharField(max_length=16)
    目标线 = models.IntegerField()
    安全线 = models.IntegerField()

    def __str__(self) -> str:
        return f"<站点配置 {self.日期} {self.站点.站点名称} {self.站点难度} 目标线={self.目标线} 安全线={self.安全线}>"
