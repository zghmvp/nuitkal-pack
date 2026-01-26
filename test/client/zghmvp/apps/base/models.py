# core
from datetime import date
from functools import lru_cache
from typing import cast

import cachetools
from django.db import models
from django.db.models.expressions import Expression

from zghmvp.apps.report.tools.models import BaseModel
from zghmvp.config import COMPANY
from zghmvp.tools.format import auto_datetime_convert
from zghmvp.tools.models import CustomAttrNameForeignKey


class Base启用停用(BaseModel):
    启用时间 = models.DateField(verbose_name="启用时间")
    停用时间 = models.DateField(verbose_name="停用时间", default=None, null=True, blank=True)  # 站点运营时间“小于”停用时间

    @classmethod
    @auto_datetime_convert
    def select_enable(cls, start_date: date, end_date: date | None = None):
        # if not end_date:
        #     query_args = models.Q(enable_date__lte=start_date) & (models.Q(disable_date__gt=start_date) | models.Q(disable_date__isnull=True))
        # else:
        #     query_args = models.Q(enable_date__lte=end_date) & (models.Q(disable_date__gte=start_date) | models.Q(disable_date__isnull=True))

        if not end_date:
            query_args = models.Q(启用时间__lte=start_date) & (models.Q(停用时间__gt=start_date) | models.Q(停用时间__isnull=True))
        else:
            query_args = models.Q(启用时间__lte=end_date) & (models.Q(停用时间__gte=start_date) | models.Q(停用时间__isnull=True))
            # 启用时间不晚于查询结束时间
            # 没有停用（永久启用） 或者 停用时间晚于查询开始时间（说明在 start_date 时还未停用）

        return cls.objects.filter(query_args)

    class Meta:
        abstract = True


class 城市(Base启用停用):
    id = models.IntegerField(primary_key=True)
    城市ID = models.GeneratedField(expression=cast(Expression, models.F("id")), output_field=models.IntegerField(unique=True), db_persist=True)
    城市名称 = models.CharField(verbose_name="城市名称", unique=True, max_length=4)

    class Meta:
        ordering = ("id",)
        unique_together = (("id",),)

    def __str__(self):
        return f"<城市 {self.城市名称}>"

    @staticmethod
    @lru_cache(maxsize=None)
    def get(**kwargs):
        return 城市.objects.get(**kwargs)


class 区域(Base启用停用):
    城市 = CustomAttrNameForeignKey(verbose_name="城市", to=城市, on_delete=models.PROTECT, db_column="城市ID", attrname="城市ID")  # type: ignore

    id = models.IntegerField(primary_key=True)
    区域ID = models.GeneratedField(expression=cast(Expression, models.F("id")), output_field=models.IntegerField(unique=True), db_persist=True)
    区域名称 = models.CharField(verbose_name="区域名称", max_length=8)

    class Meta:
        ordering = (
            "城市",
            "id",
        )
        unique_together = (("城市", "id"),)

    def __str__(self):
        return f"<区域 {self.区域名称}>"

    @staticmethod
    @lru_cache(maxsize=None)
    def get(**kwargs):
        return 区域.objects.get(**kwargs)


class 站点(Base启用停用):
    class C_状态(models.TextChoices):
        正常 = "正常", "正常"
        停用 = "停用", "停用"

    城市 = CustomAttrNameForeignKey(verbose_name=城市, to=城市, on_delete=models.PROTECT, db_column="城市ID", attrname="城市ID")  # type: ignore
    区域 = CustomAttrNameForeignKey(verbose_name=区域, to=区域, on_delete=models.PROTECT, db_column="区域ID", attrname="区域ID")  # type: ignore

    id = models.IntegerField(primary_key=True)
    站点ID = models.GeneratedField(expression=cast(Expression, models.F("id")), output_field=models.IntegerField(unique=True), db_persist=True)
    站点名称 = models.CharField(verbose_name="站点名称", max_length=8, unique=True)
    站点全称 = models.CharField(verbose_name="站点全称", max_length=18, unique=True)

    灯塔ID = models.IntegerField(verbose_name="灯塔站点ID", default=None, blank=True, null=True)
    灯塔站点名称 = models.CharField(verbose_name="灯塔站点名称", max_length=18, default=None, null=True, blank=True)

    继承站点 = CustomAttrNameForeignKey(
        verbose_name="继承站点",
        to="站点",
        on_delete=models.PROTECT,
        db_column="继承站点ID",
        attrname="继承站点ID",
        default=None,
        null=True,
        blank=True,
    )  # type: ignore
    状态 = models.CharField(verbose_name="状态", max_length=4, choices=C_状态.choices, default=C_状态.正常)

    开业日期 = models.DateField(verbose_name="开业日期", default=None, null=True, blank=True)

    class Meta:
        ordering = ("城市", "区域", "id")
        unique_together = (("城市", "区域", "id"),)

    def __str__(self):
        return f"<Site {self.站点名称}>"

    @classmethod
    @cachetools.cached(cachetools.TTLCache(maxsize=1024, ttl=10))
    def MAP(cls, attr_name, key_type=None):
        result = {"城市ID": {}, "城市名称": {}, "区域ID": {}, "区域名称": {}, "站点ID": {}, "站点全称": {}, "站点名称": {}}
        for site in cls.objects.select_related("城市", "区域"):
            key = getattr(site, attr_name)
            if key_type:
                key = key_type(key)
            result["城市ID"][key] = site.城市ID  # type: ignore
            result["城市名称"][key] = site.城市.城市名称

            result["区域ID"][key] = site.区域ID  # type: ignore
            result["区域名称"][key] = site.区域.区域名称

            result["站点ID"][key] = site.站点ID
            result["站点全称"][key] = site.站点全称
            result["站点名称"][key] = site.站点名称
        result["城市"] = result["城市名称"]
        result["区域"] = result["区域名称"]
        return result

    @classmethod
    def Name2(cls, key_type=None):
        return cls.MAP("站点名称", key_type=key_type)

    @classmethod
    def ID2(cls, key_type=None):
        return cls.MAP("id", key_type=key_type)

    @classmethod
    def 灯塔ID2(cls, key_type=None):
        return cls.MAP("灯塔ID", key_type=key_type)

    @staticmethod
    @lru_cache(maxsize=None)
    def get(**kwargs):
        return 站点.objects.get(**kwargs)


class 骑手(BaseModel):
    class C_状态(models.TextChoices):
        在职 = "在职", "在职"
        离职 = "离职", "离职"

    class C_骑手类型(models.TextChoices):
        全职 = "全职", "全职"
        兼职 = "兼职", "兼职"

        时段兼职 = "时段兼职", "时段兼职"
        普通全天兼职 = "普通全天兼职", "普通全天兼职"
        高价兼职 = "高价兼职", "高价兼职"

    class C_性别(models.TextChoices):
        男 = "男", "男"
        女 = "女", "女"

    class C_是否绑卡(models.TextChoices):
        是 = "是", "是"
        否 = "否", "否"

    class C_岗位(models.TextChoices):
        骑手 = "骑手", "骑手"
        组长 = "骑手组长", "骑手组长"
        城市经理 = "配送合作商城市经理", "配送合作商城市经理"
        区域经理 = "配送合作商区域经理", "配送合作商区域经理"

    商 = models.CharField(max_length=8, default=COMPANY)
    城市 = CustomAttrNameForeignKey(verbose_name="城市", to="城市", on_delete=models.PROTECT, db_column="城市ID", attrname="城市ID")  # type: ignore
    区域 = CustomAttrNameForeignKey(verbose_name="区域", to="区域", on_delete=models.PROTECT, db_column="区域ID", attrname="区域ID")  # type: ignore
    站点 = CustomAttrNameForeignKey(verbose_name="站点", to="站点", on_delete=models.PROTECT, db_column="站点ID", attrname="站点ID")  # type: ignore

    id = models.BigIntegerField(primary_key=True)
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=32)
    骑手ID = models.GeneratedField(expression=cast(Expression, models.F("id")), output_field=models.IntegerField(unique=True), db_persist=True)
    # 骑手类型 = models.CharField(verbose_name="骑手类型", max_length=8, choices=C_骑手类型)
    岗位 = models.CharField(verbose_name="岗位", max_length=12, choices=C_岗位.choices, default=C_岗位.骑手)
    状态 = models.CharField(verbose_name="状态", max_length=4, choices=C_状态.choices)
    性别 = models.CharField(verbose_name="性别", max_length=4, choices=C_性别.choices)

    MIS账号 = models.CharField(verbose_name="MIS账号", max_length=124, default=None, null=True, blank=True)
    是否绑卡 = models.CharField(verbose_name="是否绑卡", max_length=4, choices=C_是否绑卡.choices)

    身份证号码 = models.CharField(verbose_name="身份证号码", max_length=18, default=None, null=True, blank=True)
    手机号码 = models.CharField(verbose_name="手机号码", max_length=18, default=None, null=True, blank=True)

    账号创建时间 = models.DateTimeField(verbose_name="账号创建时间", default=None, null=True, blank=True)
    开始服务时间 = models.DateTimeField(verbose_name="开始服务时间", default=None, null=True, blank=True)
    注册时间 = models.DateTimeField(verbose_name="注册时间", default=None, null=True, blank=True)
    入职时间 = models.DateTimeField(verbose_name="入职时间", default=None, null=True, blank=True)
    离职时间 = models.DateTimeField(verbose_name="离职时间", default=None, null=True, blank=True)
    健康证过期时间 = models.DateField(verbose_name="健康证过期时间", default=None, null=True, blank=True)

    class Meta:
        ordering = ("城市", "区域", "站点", "id")
        unique_together = (("id",),)

    def __str__(self):
        return f"<骑手 {self.骑手姓名}>"
