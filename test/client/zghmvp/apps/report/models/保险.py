# core
from django.db import models

from .base import DateBaseModel


class 保险名单(DateBaseModel):
    class C_操作(models.TextChoices):
        增员 = "增员", "增员"
        减员 = "减员", "减员"

    操作 = models.CharField(verbose_name="操作", max_length=16, choices=C_操作.choices)
    平台 = models.CharField(verbose_name="平台", max_length=32)
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=32)
    骑手ID = models.IntegerField(verbose_name="骑手ID")
    身份证号码 = models.CharField(verbose_name="身份证号码", max_length=18)

    操作时间 = models.DateTimeField(verbose_name="操作时间", auto_now_add=True, null=True, blank=True)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手ID")
        unique_together = (("日期", "骑手ID"),)
