# core
from django.db import models

from .base import DateBaseModel


class 灯塔_考核奖惩_站点运力考核目标(DateBaseModel):
    运力目标 = models.IntegerField()

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("站点", "日期"),)
