# core
from django.db import models

from zghmvp.apps.base import models as base_models
from zghmvp.config import COMPANY
from zghmvp.tools.models import BaseModel, CustomAttrNameForeignKey

from .base import DateBaseModel
from .灯塔_订单 import 灯塔_订单_城市区域


class __看板_订单_Base(DateBaseModel):
    """旧看板订单"""

    完成日期 = models.DateField(verbose_name="完成日期", null=True, blank=True, db_index=True)

    订单ID = models.BigIntegerField(verbose_name="订单ID", db_index=True)
    揽收号 = models.CharField(verbose_name="揽收号", max_length=8, default="")
    来源 = models.CharField(verbose_name="来源", max_length=8, default="")
    履约单类型 = models.CharField(verbose_name="履约单类型", max_length=8, default="")
    履约方式 = models.CharField(verbose_name="履约方式", max_length=8, default="")
    时效包 = models.CharField(verbose_name="时效包", max_length=8, default="")
    骑手mis号 = models.CharField(verbose_name="骑手mis号", max_length=32, default=None, null=True, blank=True)
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=32, default=None, null=True, blank=True)
    履约单创建时间 = models.DateTimeField(verbose_name="履约单创建时间", default=None, null=True, blank=True)
    整体履约时长 = models.FloatField(verbose_name="整体履约时长", default=0)
    商品总数 = models.IntegerField(verbose_name="商品总数", default=0)
    站内履约时长 = models.FloatField(verbose_name="站内履约时长", default=0)
    备餐时长 = models.FloatField(verbose_name="备餐时长", default=0)
    分拣时长 = models.FloatField(verbose_name="分拣时长", default=0)
    打包时长 = models.FloatField(verbose_name="打包时长", default=0)
    推配送时间 = models.DateTimeField(verbose_name="推配送时间", db_index=True, default=None, null=True, blank=True)
    骑手接单时间 = models.DateTimeField(verbose_name="骑手接单时间", default=None, null=True, blank=True)
    骑手揽收时间 = models.DateTimeField(verbose_name="骑手揽收时间", default=None, null=True, blank=True)
    配送完成时间 = models.DateTimeField(verbose_name="配送完成时间", default=None, null=True, blank=True)
    配送时长 = models.FloatField(verbose_name="配送时长", default=0)
    是否整体超时 = models.CharField(verbose_name="是否整体超时", max_length=2, default="")
    是否站内履约超时 = models.CharField(verbose_name="是否站内履约超时", max_length=2, default="")
    是否配送超时 = models.CharField(verbose_name="是否配送超时", max_length=2, default="")
    分拣员 = models.CharField(verbose_name="分拣员", max_length=64, default="")
    打包员 = models.CharField(verbose_name="打包员", max_length=32, default="")
    异常类型 = models.CharField(verbose_name="异常类型", max_length=128, default="")
    订单备注 = models.CharField(verbose_name="订单备注", max_length=255, default="")

    class Meta:
        managed = True  # Django 不尝试创建或校验约束
        abstract = True
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("订单ID", "日期"),)


class 看板_订单(__看板_订单_Base):
    pass


class 看板_实时订单(__看板_订单_Base):
    pass


class 看板_订单_骑手(DateBaseModel):
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=64)
    骑手mis号 = models.CharField(verbose_name="骑手mis号", max_length=32)
    骑手ID = models.IntegerField(default=0, blank=True)

    是否大网骑手 = models.CharField(verbose_name="是否大网骑手", default="否", max_length=4)
    推配单量 = models.IntegerField(verbose_name="推配单量", default=0)
    接单量 = models.IntegerField(verbose_name="接单量", default=0)
    推配完成单量 = models.IntegerField(verbose_name="推配完成单量", default=0)  # 根据推配送日期计算完成单量
    完成单量 = models.IntegerField(verbose_name="完成单量", default=0)
    夜配完成单量 = models.IntegerField(verbose_name="夜配完成单量", default=0)  # 用当天的订单计算出来的
    高峰期完成单量 = models.IntegerField(verbose_name="高峰期完成单量", default=0)
    午高峰完成单量 = models.IntegerField(verbose_name="午高峰完成单量", default=0)
    晚高峰完成单量 = models.IntegerField(verbose_name="晚高峰完成单量", default=0)
    全天单量是否达成 = models.CharField(verbose_name="全天单量是否达成", default="否", max_length=4)
    午高峰单量是否达成 = models.CharField(verbose_name="午高峰单量是否达成", default="否", max_length=4)
    晚高峰单量是否达成 = models.CharField(verbose_name="晚高峰单量是否达成", default="否", max_length=4)
    高峰期单量是否达成 = models.CharField(verbose_name="高峰期单量是否达成", default="否", max_length=4)
    有效运力是否达成 = models.CharField(verbose_name="有效运力是否达成", default="否", max_length=4)

    超时单量 = models.IntegerField(verbose_name="超时单量", default=0)
    异常上报单量 = models.IntegerField(verbose_name="异常上报单量", default=0)

    推配时段明细 = models.JSONField(verbose_name="推配时段", default=list)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手mis号")
        unique_together = (("站点", "骑手姓名", "骑手mis号", "日期", "是否大网骑手"),)


class __看板_订单_城市区域站点(BaseModel):
    大网单量 = models.IntegerField(verbose_name="大网单量", default=0)
    推配完成单量 = models.IntegerField(verbose_name="推配完成单量", default=0)  # 根据推配送日期计算完成单量 不含大网
    完成单量 = models.IntegerField(verbose_name="完成单量", default=0)
    夜配完成单量 = models.IntegerField(verbose_name="夜配完成单量", default=0)  # 用当天的订单计算出来的
    高峰期完成单量 = models.IntegerField(verbose_name="高峰期完成单量", default=0)
    午高峰完成单量 = models.IntegerField(verbose_name="午高峰完成单量", default=0)
    晚高峰完成单量 = models.IntegerField(verbose_name="晚高峰完成单量", default=0)
    月累计完成单量 = models.IntegerField(verbose_name="月累计完成单量", default=0)
    月工作日完成单量 = models.IntegerField(verbose_name="月工作日完成单量", default=0)
    月工作日日均单量 = models.IntegerField(verbose_name="月工作日日均单量", default=0)
    月非工作日完成单量 = models.IntegerField(verbose_name="月非工作日完成单量", default=0)
    月非工作日日均单量 = models.IntegerField(verbose_name="月非工作日日均单量", default=0)
    月预估单量 = models.IntegerField(verbose_name="月预估单量", default=0)

    跑单骑手 = models.IntegerField(verbose_name="跑单骑手", default=0)  # 有跑单的骑手统计（不含大网）
    出勤骑手 = models.IntegerField(verbose_name="出勤骑手", default=0)
    有单骑手 = models.IntegerField(verbose_name="有单骑手", default=0)
    人效骑手 = models.IntegerField(verbose_name="人效骑手", default=0)
    人效 = models.FloatField(verbose_name="人效", default=0)

    有效运力达成骑手数 = models.IntegerField(verbose_name="有效运力达成骑手数", default=0)
    运力目标 = models.IntegerField(verbose_name="运力目标", default=0)
    运力考核 = models.IntegerField(verbose_name="运力考核", default=0)
    出勤未达成 = models.IntegerField(verbose_name="出勤未达成", default=0)  # 出勤骑手 - 有效运力达成骑手数
    运力达成率 = models.FloatField(verbose_name="运力达成率", default=0)  #  运力考核 / 运力目标
    运力满足率 = models.FloatField(verbose_name="运力满足率", default=0)  #  出勤骑手 / 运力目标
    运力缺口 = models.IntegerField(verbose_name="运力缺口", default=0)  #  出勤骑手 - 运力目标
    运力达成差值 = models.IntegerField(verbose_name="运力达成差值", default=0)  #  有效运力达成 - 运力目标
    出勤未达成数 = models.IntegerField(
        verbose_name="出勤未达成数", default=0
    )  #  numpy.where(df_站点单量明细["运力达成率"] == 1, 0, df_站点单量明细["有单骑手数"] - df_站点单量明细["有效运力达成"])

    全天单量未达成骑手数 = models.IntegerField(verbose_name="全天单量未达成骑手数", default=0)
    午高峰单量未达成骑手数 = models.IntegerField(verbose_name="午高峰单量未达成骑手数", default=0)
    晚高峰单量未达成骑手数 = models.IntegerField(verbose_name="晚高峰单量未达成骑手数", default=0)
    高峰期单量未达成骑手数 = models.IntegerField(verbose_name="高峰期单量未达成骑手数", default=0)

    超时单量 = models.IntegerField(verbose_name="超时单量", default=0)
    异常上报单量 = models.IntegerField(verbose_name="异常上报单量", default=0)

    推配时段明细 = models.JSONField(verbose_name="推配时段", default=list)

    class Meta:
        abstract = True


class 看板_订单_站点(DateBaseModel, __看板_订单_城市区域站点):
    月工作日天数 = models.IntegerField(verbose_name="月工作日天数", default=0)
    月非工作日天数 = models.IntegerField(verbose_name="月非工作日天数", default=0)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("站点", "日期"),)


class 看板_订单_城市区域(__看板_订单_城市区域站点):
    C_数据类别 = 灯塔_订单_城市区域.C_数据类别

    商 = models.CharField(max_length=8, default=COMPANY, null=True, blank=True)
    城市 = CustomAttrNameForeignKey(
        verbose_name="城市",
        null=True,
        blank=True,
        default=None,
        to=base_models.城市,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="城市ID",
        attrname="城市ID",
        db_constraint=False,
    )  # type: ignore
    区域 = CustomAttrNameForeignKey(
        verbose_name="区域",
        null=True,
        blank=True,
        default=None,
        to=base_models.区域,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="区域ID",
        attrname="区域ID",
        db_constraint=False,
    )  # type: ignore
    日期 = models.DateField(verbose_name="日期", db_index=True)

    数据类别 = models.CharField(verbose_name="数据类别", max_length=8, default="", choices=C_数据类别.choices)

    class Meta:
        ordering = ("-日期", "城市", "区域")
        unique_together = (("商", "城市", "区域", "日期"),)
