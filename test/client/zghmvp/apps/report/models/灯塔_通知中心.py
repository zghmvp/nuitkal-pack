# core

from django.db import models

from zghmvp.tools.models import BaseModel


class 灯塔_通知中心_通知列表(BaseModel):
    推送时间 = models.DateField()
    标题 = models.CharField(max_length=255)
    通知类型 = models.CharField(max_length=32)
    发布人 = models.CharField(max_length=32)
    内容 = models.TextField(default="")
    附件 = models.JSONField(default=list)
    详情 = models.JSONField(default=dict)
