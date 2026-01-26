# core

from django.db import models

from .base import DateBaseModel


class 灯塔_质控_判责清单_超时与取消单(DateBaseModel):
    订单ID = models.BigIntegerField()
    配送单ID = models.CharField(max_length=16, default="")
    问题单类型 = models.CharField(max_length=6, default="")
    订单来源 = models.CharField(max_length=16, default="")
    订单类型 = models.CharField(max_length=8, default="")
    骑手姓名 = models.CharField(max_length=20)
    骑手ID = models.IntegerField(default=0, blank=True)
    配送单状态 = models.CharField(max_length=8, default="")
    是否严重超时 = models.CharField(max_length=32, default="")
    预计送达时间 = models.DateTimeField(null=True, blank=True)
    配送单创建时间 = models.DateTimeField(null=True, blank=True)
    派单时间 = models.DateTimeField(null=True, blank=True)
    取货时间 = models.DateTimeField(null=True, blank=True)
    离店时间 = models.DateTimeField(null=True, blank=True)
    送达时间 = models.DateTimeField(null=True, blank=True)
    完成时间 = models.DateTimeField(null=True, blank=True)
    订单取消时间 = models.DateTimeField(null=True, blank=True)
    异常上报 = models.CharField(max_length=1024, default="")
    申诉描述 = models.CharField(max_length=1024, default="")
    初判结果 = models.CharField(max_length=8, default="")
    终判结果 = models.CharField(max_length=8, default="")
    不通过理由 = models.CharField(max_length=64, default="")
    是否申诉 = models.CharField(max_length=8, default="")
    申诉状态 = models.CharField(max_length=8, default="")
    工单创建时间 = models.DateTimeField()
    一申时间 = models.DateTimeField(null=True, blank=True)
    初判时间 = models.DateTimeField(null=True, blank=True)
    二申时间 = models.DateTimeField(null=True, blank=True)
    终判时间 = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("订单ID", "配送单ID", "问题单类型"),)


class 灯塔_质控_判责清单_客诉(DateBaseModel):
    订单ID = models.BigIntegerField()
    异常问题单ID = models.CharField(max_length=16, unique=True)
    工单ID = models.CharField(max_length=16)
    骑手姓名 = models.CharField(max_length=20)
    骑手ID = models.IntegerField(default=0, blank=True)
    问题单类型 = models.CharField(max_length=6, default="")
    客诉渠道 = models.CharField(max_length=6)
    客诉类别_评价标签 = models.CharField(max_length=64)
    问题反馈 = models.TextField(default="")
    申诉描述 = models.CharField(max_length=2048, default="")
    客诉skuId = models.CharField(max_length=32, default="")
    客诉sku名称 = models.CharField(max_length=64, default="")
    初判结果 = models.CharField(max_length=4)
    终判结果 = models.CharField(max_length=4)
    不通过理由 = models.CharField(max_length=1024, default="")
    是否申诉 = models.CharField(max_length=4)
    申诉状态 = models.CharField(max_length=8)
    客诉时间 = models.DateTimeField()
    工单创建时间 = models.DateTimeField(default=None, null=True, blank=True)
    一申时间 = models.DateTimeField(default=None, null=True, blank=True)
    初判时间 = models.DateTimeField(default=None, null=True, blank=True)
    二申时间 = models.DateTimeField(default=None, null=True, blank=True)
    终判时间 = models.DateTimeField(default=None, null=True, blank=True)

    工单图片 = models.JSONField(default=list)
    申诉判责结果 = models.CharField(max_length=4, default="")
    申诉材料 = models.JSONField(default=list)
    指定位置拍照 = models.JSONField(default=list)
    推配送时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手揽收时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手离店时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手送达时间 = models.DateTimeField(default=None, null=True, blank=True)
    最晚送达时间 = models.DateTimeField(default=None, null=True, blank=True)
    是否超时 = models.CharField(max_length=4, default="")

    @classmethod
    def 有责订单(cls):
        return cls.objects.exclude(终判结果__in=["无责"]).exclude(申诉状态__in=["一申通过", "二申通过"])
