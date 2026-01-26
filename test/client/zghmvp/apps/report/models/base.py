# core

from django.db import models

from zghmvp.apps.base import models as base_models
from zghmvp.apps.report.tools.models import BaseModel
from zghmvp.config import COMPANY
from zghmvp.tools.models import CustomAttrNameForeignKey


class DateBaseModel(BaseModel):
    商 = models.CharField(max_length=8, default=COMPANY)
    # db_constraint=False 删除外键约束
    城市 = CustomAttrNameForeignKey(
        verbose_name="城市ID",
        to=base_models.城市,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="城市ID",
        attrname="城市ID",
        db_constraint=False,
    )  # type: ignore
    区域 = CustomAttrNameForeignKey(
        verbose_name="区域ID",
        to=base_models.区域,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="区域ID",
        attrname="区域ID",
        db_constraint=False,
    )  # type: ignore
    站点 = CustomAttrNameForeignKey(
        verbose_name="站点ID",
        to=base_models.站点,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="站点ID",
        attrname="站点ID",
        db_constraint=False,
    )  # type: ignore
    日期 = models.DateField(verbose_name="日期", db_index=True)

    class Meta:
        abstract = True


class QueryStatusModel(BaseModel):
    key = models.CharField(max_length=32, db_index=True)
    status = models.BooleanField(verbose_name="状态", default=True)
