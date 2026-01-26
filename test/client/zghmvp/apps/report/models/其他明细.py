# core
import polars
from django.db import models, transaction

from zghmvp.apps.base import models as base_models
from zghmvp.config import COMPANY
from zghmvp.tools.models import BaseModel, CustomAttrNameForeignKey
from zghmvp.tools.pl import PlTools


class 其他明细(BaseModel):
    商 = models.CharField(max_length=8, default=COMPANY, null=True, blank=True)
    城市 = CustomAttrNameForeignKey(
        verbose_name="城市",
        to=base_models.城市,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="城市ID",
        attrname="城市ID",
        default=None,
        null=True,
        blank=True,
        db_constraint=False,
    )  # type: ignore
    区域 = CustomAttrNameForeignKey(
        verbose_name="区域",
        to=base_models.区域,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="区域ID",
        attrname="区域ID",
        default=None,
        null=True,
        blank=True,
        db_constraint=False,
    )  # type: ignore
    站点 = CustomAttrNameForeignKey(
        verbose_name="站点",
        to=base_models.站点,
        db_index=True,
        on_delete=models.PROTECT,
        db_column="站点ID",
        attrname="站点ID",
        default=None,
        null=True,
        blank=True,
        db_constraint=False,
    )  # type: ignore
    日期 = models.DateField(verbose_name="日期", db_index=True)

    name = models.CharField(max_length=125)
    data = models.JSONField()

    @classmethod
    def to_dataframe(cls, query_set: models.QuerySet):
        return polars.DataFrame([dict(item) for item in query_set.values_list("data", flat=True)])

    @classmethod
    def db_save(cls, df: polars.DataFrame, name: str):
        df = PlTools.date_2_str(df)
        with transaction.atomic():
            cls.objects.filter(站点ID__in=df["站点ID"].unique(), 日期__in=df["日期"].unique(), name=name).delete()
            create_list = []
            for item in df.iter_rows(named=True):
                create_list.append(cls(城市ID=item["城市ID"], 区域ID=item["区域ID"], 站点ID=item["站点ID"], 日期=item["日期"], name=name, data=[(k, v) for k, v in item.items()]))
            return cls.objects.bulk_create(create_list, ignore_conflicts=False)
