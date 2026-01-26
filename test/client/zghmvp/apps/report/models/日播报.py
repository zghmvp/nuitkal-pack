# core
from django.db import models

from zghmvp.apps.base import models as base_models
from zghmvp.config import COMPANY
from zghmvp.tools.models import BaseModel, CustomAttrNameForeignKey


class 日播报(BaseModel):
    日期 = models.DateField(db_index=True)
    类型 = models.CharField(max_length=4, choices=(("商", "商"), ("城市", "城市"), ("区域", "区域"), ("站点", "站点")))

    商 = models.CharField(max_length=8, default=COMPANY, null=True, blank=True)
    城市 = CustomAttrNameForeignKey(
        verbose_name="城市",
        to=base_models.城市,
        on_delete=models.PROTECT,
        db_column="城市ID",
        attrname="城市ID",
        null=True,
        blank=True,
        default=None,
        db_constraint=False,
    )  # type: ignore
    区域 = CustomAttrNameForeignKey(
        verbose_name="区域",
        to=base_models.区域,
        on_delete=models.PROTECT,
        db_column="区域ID",
        attrname="区域ID",
        null=True,
        blank=True,
        default=None,
        db_constraint=False,
    )  # type: ignore
    站点 = CustomAttrNameForeignKey(
        verbose_name="站点",
        to=base_models.站点,
        on_delete=models.PROTECT,
        db_column="站点ID",
        attrname="站点ID",
        null=True,
        blank=True,
        default=None,
        db_constraint=False,
    )  # type: ignore

    数据 = models.JSONField()

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = ("日期", "类型", "城市", "区域", "站点")
