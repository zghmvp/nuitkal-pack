# core
from django.db import models

from .base import DateBaseModel


class 灯塔_申诉中心_违规申诉(DateBaseModel):
    骑手姓名 = models.CharField(max_length=32, null=True, blank=True)
    骑手ID = models.IntegerField(default=0)

    违规项ID = models.BigIntegerField()
    违规类型 = models.CharField(max_length=16)
    责任方 = models.CharField(max_length=8, default="骑手")
    责任方信息 = models.CharField(max_length=20)
    责任方ID = models.BigIntegerField()
    订单ID = models.BigIntegerField(default=None, null=True, blank=True)
    配送单ID = models.CharField(max_length=16, default="")
    违规创建时间 = models.DateTimeField(default=None, null=True, blank=True)
    违规状态 = models.CharField(max_length=16)
    申诉状态 = models.CharField(max_length=16)
    # 订单明细匹配
    推配送时间 = models.DateTimeField(default=None, null=True, blank=True, db_index=True)
    异常上报原因 = models.JSONField(default=list)
    骑手接单时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手揽收时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手离店时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手取消时间 = models.DateTimeField(default=None, null=True, blank=True)
    首次接通时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手送达时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手考核时间 = models.DateTimeField(default=None, null=True, blank=True)
    通话记录 = models.JSONField(default=list)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("违规项ID", "违规类型", "订单ID", "配送单ID"),)

    @classmethod
    def 有责订单(cls):
        return cls.objects.exclude(申诉状态__in=["申诉通过"]).exclude(违规状态="已作废")
