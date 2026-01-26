# core
from django.db import models

from .base import DateBaseModel


class 灯塔_排班管理_站点排班(DateBaseModel):
    天气 = models.CharField(verbose_name="天气", max_length=16)
    全职排班 = models.IntegerField(verbose_name="全职排班", default=0)
    全职出勤 = models.IntegerField(verbose_name="全职出勤", default=0)
    全职排班率 = models.FloatField(verbose_name="全职排班率", default=0)


class 灯塔_排班管理_骑手排班(DateBaseModel):
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=32, db_index=True)
    骑手ID = models.IntegerField(verbose_name="骑手ID")
    工作时长 = models.CharField(verbose_name="工作时长", max_length=16)
    班次 = models.CharField(verbose_name="班次", max_length=16)
    排班时间 = models.JSONField(verbose_name="排班时间", default=list)


class 灯塔_排班管理_站点时段排班(DateBaseModel):
    时段名称 = models.CharField(verbose_name="时段名称", max_length=16)
    开始时间 = models.DateTimeField(verbose_name="开始时间")
    结束时间 = models.DateTimeField(verbose_name="结束时间")
    预估推配送单量 = models.IntegerField(verbose_name="预估推配送单量", default=0)
    建议骑手人数 = models.IntegerField(verbose_name="建议骑手人数", default=0)
    排班骑手人数 = models.IntegerField(verbose_name="排班骑手人数", default=0)
    增减人数建议 = models.IntegerField(verbose_name="增减人数建议", default=0)
