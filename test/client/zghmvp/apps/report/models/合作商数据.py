# core


from django.db import models

from .base import DateBaseModel


class 核心数据(DateBaseModel):
    系统恶劣天气标签 = models.CharField(max_length=4)
    恶劣天气订单占比 = models.FloatField(default=0)
    配送准时率 = models.FloatField(default=0)
    复合严重超时率 = models.FloatField(default=0)
    有效骑手出勤人数 = models.IntegerField(default=0)
    配送客诉率 = models.FloatField(default=0)
    配送差评率 = models.FloatField(default=0)
    违规点送达率 = models.FloatField(default=0)
    配送原因未完成订单占比 = models.FloatField(default=0)
    配送原因未完成订单占比_未完成全部当作取消 = models.FloatField(default=0)
    配送完成率 = models.FloatField(default=0)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("站点", "日期"),)


class 排班数据明细(DateBaseModel):
    天气状况 = models.CharField(max_length=8, default="")
    营业天数 = models.IntegerField(default=0)

    全天排班骑手数 = models.IntegerField(default=0)
    有效出勤骑手数据 = models.IntegerField(default=0)
    排班出勤准确率 = models.FloatField(default=0)

    出勤小时数不含休息 = models.IntegerField(default=0)
    计划外出勤小时数 = models.IntegerField(default=0)
    计划外出勤占比 = models.FloatField(default=0)

    全天考核排班骑手数 = models.IntegerField(default=0)
    全天排班出勤合格数 = models.IntegerField(default=0)
    全天排班出勤合格率 = models.FloatField(default=0)

    午高峰排班骑手数 = models.IntegerField(default=0)
    午高峰排班出勤合格数 = models.IntegerField(default=0)
    午高峰排班出勤合格率 = models.FloatField(default=0)

    晚高峰排班骑手数 = models.IntegerField(default=0)
    晚高峰排班出勤合格数 = models.IntegerField(default=0)
    晚高峰排班出勤合格率 = models.FloatField(default=0)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("日期", "站点"),)


class 骑手出勤明细(DateBaseModel):
    骑手姓名 = models.CharField(max_length=32)
    骑手ID = models.IntegerField(default=0)

    天气状况 = models.CharField(max_length=8, default="")
    排班 = models.CharField(max_length=32, default="")

    首单接单时间 = models.DateTimeField(default=None, null=True, blank=True)
    首次入店时间 = models.DateTimeField(default=None, null=True, blank=True)
    排班开始时间 = models.DateTimeField(default=None, null=True, blank=True)
    最后一单送达时间 = models.DateTimeField(default=None, null=True, blank=True)
    排班结束时间 = models.DateTimeField(default=None, null=True, blank=True)
    休息开始时间 = models.DateTimeField(default=None, null=True, blank=True)
    休息结束时间 = models.DateTimeField(default=None, null=True, blank=True)

    是否有效出勤 = models.CharField(max_length=8, default="")
    出勤状态 = models.CharField(max_length=16, default="")
    出勤小时数不含休息 = models.IntegerField(default=0)
    排班小时数不含休息 = models.IntegerField(default=0)
    计划外出勤小时数 = models.IntegerField(default=0)
    午高峰完单 = models.IntegerField(default=0)
    晚高峰完单 = models.IntegerField(default=0)
    全天完单 = models.IntegerField(default=0)

    全天工作时长 = models.FloatField(default=0)
    午高峰工作时长 = models.FloatField(default=0)
    晚高峰工作时长 = models.FloatField(default=0)
    全天排班时长 = models.FloatField(default=0)
    午高峰排班时长 = models.FloatField(default=0)
    晚高峰排班时长 = models.FloatField(default=0)
    是否新骑手 = models.CharField(max_length=8, default="")
    全天是否出勤合格 = models.CharField(max_length=8, default="")
    午高峰是否出勤合格 = models.CharField(max_length=8, default="")
    晚高峰是否出勤合格 = models.CharField(max_length=8, default="")

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手ID")
        unique_together = (("日期", "站点", "骑手ID", "排班"),)


class 配送原因取消明细(DateBaseModel):
    订单ID = models.BigIntegerField()
    订单类型 = models.CharField(max_length=4)
    时效包 = models.IntegerField()
    推配送时间 = models.DateTimeField()
    订单计划推配送时间 = models.DateTimeField()
    最早异常上报时间 = models.DateTimeField()
    预计最晚送达时间 = models.DateTimeField()
    取消时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手mis = models.CharField(max_length=64, default="")
    骑手姓名 = models.CharField(max_length=20, default="")
    骑手ID = models.IntegerField(default=0)

    履约单号 = models.CharField(verbose_name="履约单号", max_length=32, default="")
    是否外卖单 = models.CharField(max_length=4)
    异常上报类型 = models.CharField(max_length=32, default="")
    异常上报时间 = models.DateTimeField(default=None, null=True, blank=True)
    是否大网单 = models.CharField(max_length=4)
    用户或客服选择原因 = models.CharField(max_length=16)
    判责结果 = models.CharField(max_length=8)
    派送记录 = models.TextField()

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手ID")
        unique_together = (("日期", "骑手ID", "订单ID"),)

    @classmethod
    def 有责订单(cls):
        return cls.objects.exclude(判责结果__in=["申诉无责", "系统前置无责", "无责"])


class 配送超时明细(DateBaseModel):
    订单ID = models.BigIntegerField()
    配送单ID = models.CharField(max_length=16)
    订单来源 = models.CharField(max_length=16)
    订单类型 = models.CharField(max_length=3)
    时效包 = models.IntegerField()
    配送类型 = models.CharField(max_length=6, default="")
    骑手姓名 = models.CharField(max_length=20, default="")
    骑手ID = models.IntegerField(default=0)
    履约单号 = models.CharField(verbose_name="履约单号", max_length=32, default="")
    最早异常上报时间 = models.DateTimeField()
    最晚异常上报时间 = models.DateTimeField()
    预约单预计送达开始时间 = models.DateTimeField()
    配送考核时间 = models.DateTimeField()
    推配送时间 = models.DateTimeField()
    骑手接单时间 = models.DateTimeField(default=None, null=True, blank=True)
    骑手送达时间 = models.DateTimeField(default=None, null=True, blank=True)
    异常上报时间 = models.DateTimeField(default=None, null=True, blank=True)
    异常上报类型 = models.CharField(max_length=16, default="")
    超时时间 = models.FloatField(default=0)
    降级后超时类型 = models.CharField(max_length=20)
    是否大网单 = models.CharField(max_length=4)
    派送记录 = models.TextField()

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手ID")
        unique_together = (("日期", "骑手ID", "订单ID"),)


class 客诉明细(DateBaseModel):
    """美团的客诉以“关单日期”为准"""

    关单日期 = models.DateField()

    订单ID = models.BigIntegerField()
    客诉单号 = models.CharField(max_length=32)
    末级问题名称 = models.CharField(max_length=64)
    客诉类别 = models.CharField(max_length=32)
    骑手姓名 = models.CharField(max_length=20, default="")
    骑手ID = models.IntegerField(default=0)
    履约单号 = models.CharField(verbose_name="履约单号", max_length=32, default="")
    问题反馈 = models.TextField(default="")
    是否大网单 = models.CharField(max_length=4)
    判责结果 = models.CharField(max_length=16)
    # 订单明细匹配
    推配送时间 = models.DateTimeField(default=None, null=True, blank=True)
    # 灯塔客诉明细匹配
    用户问题反馈 = models.CharField(max_length=2048, default="")
    申诉描述 = models.CharField(max_length=2048, default="")
    客诉sku名称 = models.CharField(max_length=64, default="")
    不通过理由 = models.CharField(max_length=2048, default="")
    申诉状态 = models.CharField(max_length=8, default="")
    客诉时间 = models.DateTimeField(default=None, null=True, blank=True)
    工单创建时间 = models.DateTimeField(default=None, null=True, blank=True)
    客诉属性 = models.CharField(max_length=12, default="")

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        # unique_together = (("站点", "日期", "客诉单号"), )

    @classmethod
    def 有责订单(cls):
        return cls.objects.exclude(判责结果__in=["申诉无责", "系统前置无责", "无责"]).exclude(申诉状态__in=["一申通过", "二申通过"])


class 违规点送达明细(DateBaseModel):
    订单ID = models.BigIntegerField()
    骑手姓名 = models.CharField(max_length=20, default="")
    骑手ID = models.IntegerField(default=0)
    履约单号 = models.CharField(verbose_name="履约单号", max_length=32, default="")

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("站点", "日期", "订单ID"),)
