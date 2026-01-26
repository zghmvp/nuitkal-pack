# core
from datetime import datetime, timedelta

from django.db import models

from zghmvp.apps.base import models as base_models
from zghmvp.config import COMPANY
from zghmvp.tools.models import BaseModel, CustomAttrNameForeignKey

from .base import DateBaseModel


class 灯塔_订单(DateBaseModel):
    """注意!!! verbose_name的名称要与excel文件中的列名一致"""

    完成日期 = models.DateField(verbose_name="完成日期", null=True, blank=True, db_index=True)

    订单号 = models.BigIntegerField(verbose_name="订单号", db_index=True)
    履约单号 = models.CharField(verbose_name="履约单号", max_length=32, default=None, null=True, blank=True)
    是否三方运力 = models.CharField(verbose_name="是否三方运力", db_index=True, max_length=4)
    骑手mis号 = models.CharField(verbose_name="骑手mis号", max_length=32, default=None, null=True, blank=True)
    骑手姓名 = models.CharField(verbose_name="骑手姓名", max_length=64, default=None, null=True, blank=True)
    推配送时间 = models.DateTimeField(verbose_name="推配送时间", db_index=True)
    骑手取货时间 = models.DateTimeField(verbose_name="骑手取货时间", default=None, null=True, blank=True)
    预计送达时间 = models.DateTimeField(verbose_name="预计送达时间", default=None, null=True, blank=True)
    骑手考核时间 = models.DateTimeField(verbose_name="骑手考核时间", default=None, null=True, blank=True)
    配送完成时间 = models.DateTimeField(verbose_name="配送完成时间", default=None, null=True, blank=True)
    是否配送超时 = models.CharField(verbose_name="是否配送超时", max_length=4)
    配送超时类型 = models.CharField(verbose_name="配送超时类型", max_length=12, default=None, null=True, blank=True)
    预约单是否提前送达 = models.CharField(verbose_name="预约单是否提前送达", max_length=4)

    @classmethod
    def 计算超时类型(cls, 考核时间: datetime, 送达时间: datetime):
        # 计算超时类型
        if 考核时间 and 送达时间:
            if 送达时间 > 考核时间:
                v = (送达时间 - 考核时间).seconds

                if v >= 60 * 60:
                    return "60+超时"
                elif v >= 60 * 30:
                    return "30-60超时"
                elif v >= 60 * 10:
                    return "10-30超时"
                else:
                    return "普通超时"
            else:
                return ""
        else:
            return ""

    class Meta:
        unique_together = (("订单号", "日期"),)
        # ========== 设置手动管理数据库 ========== #
        managed = True  # Django 不尝试创建或校验约束
        """物理分区表设置，执行一次即可
        -- 变量表名 DROP SEQUENCE IF EXISTS report_灯塔_订单_id_seq;
        DO $$
        DECLARE
            tbl_main TEXT := 'report_灯塔_订单';
            y INTEGER;
            m INTEGER;
            start_date DATE;
            end_date DATE;
            part_name TEXT;
            part_tbl TEXT;
            idx TEXT;
            cols TEXT[] := ARRAY['城市ID', '区域ID', '站点ID', '日期', '完成日期', '订单号', '是否三方运力']; -- 为每个分区设置的索引
            col TEXT;
        BEGIN
            ---------------------------
            -- 创建主表（分区表）
            ---------------------------
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I (
                    id BIGSERIAL,
                    "商" VARCHAR(8),
                    "城市ID" BIGINT,
                    "区域ID" BIGINT,
                    "站点ID" BIGINT,
                    "日期" DATE NOT NULL,
                    "完成日期" DATE,
                    "订单号" VARCHAR(32) NOT NULL,
                    "履约单号" VARCHAR(32) DEFAULT '''',
                    "是否三方运力" VARCHAR(4) DEFAULT '''',
                    "骑手mis号" VARCHAR(32) DEFAULT '''',
                    "骑手姓名" VARCHAR(64) DEFAULT '''',
                    "推配送时间" TIMESTAMP NOT NULL,
                    "骑手取货时间" TIMESTAMP,
                    "预计送达时间" TIMESTAMP,
                    "骑手考核时间" TIMESTAMP,
                    "配送完成时间" TIMESTAMP,
                    "是否配送超时" VARCHAR(4) DEFAULT '''',
                    "配送超时类型" VARCHAR(12) DEFAULT '''',
                    "预约单是否提前送达" VARCHAR(4) DEFAULT '''',
                    PRIMARY KEY ("订单号", "日期")
                ) PARTITION BY RANGE ("日期");
            ', tbl_main);

            ---------------------------
            -- 创建2024-2028按月分区
            ---------------------------
            FOR y IN 2024..2028 LOOP
                FOR m IN 1..12 LOOP
                    start_date := to_date(y || '-' || m || '-01', 'YYYY-MM-DD');
                    end_date := (start_date + INTERVAL '1 month');
                    part_name := format('%s_%s_%s', tbl_main, y, lpad(m::text, 2, '0'));
                    
                    EXECUTE format('
                        CREATE TABLE IF NOT EXISTS %I
                        PARTITION OF %I
                        FOR VALUES FROM (%L) TO (%L);
                    ', part_name, tbl_main, start_date, end_date);
                END LOOP;
            END LOOP;

            ---------------------------
            -- 默认分区（超出范围）
            ---------------------------
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I
                PARTITION OF %I
                DEFAULT;
            ', tbl_main || '_default', tbl_main);

            ---------------------------
            -- 为各分区创建索引（循环列）
            ---------------------------
            FOR part_tbl IN
                SELECT relname
                FROM pg_class c
                JOIN pg_inherits i ON i.inhrelid = c.oid
                WHERE i.inhparent = tbl_main::regclass
            LOOP
                idx := replace(part_tbl, '"', ''); -- 去掉引号，确保索引名合法

                FOREACH col IN ARRAY cols LOOP
                    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%s_%s ON %I ("%s");', idx, col, part_tbl, col);
                END LOOP;
            END LOOP;

        END $$;
        """
        # ========== END 设置手动管理数据库 ========== #
        # ========== psql 导出为csv文件，从csv文件中导入数据 ========== #
        """导出为csv文件（指定列顺序）
COPY report_灯塔_订单_temp ("id", "商", "日期", "完成日期", "订单号", "履约单号", "是否三方运力", "骑手mis号", "骑手姓名", "推配送时间", "骑手取货时间", "预计送达时间", "骑手考核时间", "配送完成时间", "是否配送超时", "配送超时类型", "预约单是否提前送达", "区域ID", "城市ID", "站点ID") TO 'd:/d1.csv' WITH CSV HEADER ENCODING 'UTF8';
        """
        """从csv文件中导入数据到指定表中（指定列顺序）
COPY report_灯塔_订单 ("id", "商", "日期", "完成日期", "订单号", "履约单号", "是否三方运力", "骑手mis号", "骑手姓名", "推配送时间", "骑手取货时间", "预计送达时间", "骑手考核时间", "配送完成时间", "是否配送超时", "配送超时类型", "预约单是否提前送达", "区域ID", "城市ID", "站点ID") FROM 'd:/d1.csv' WITH CSV HEADER ENCODING 'UTF8';
        """


class 灯塔_实时订单(DateBaseModel):
    订单号 = models.BigIntegerField(verbose_name="订单号", db_index=True)
    履约状态 = models.CharField(max_length=16)
    配送剩余时间 = models.CharField(max_length=16)
    履约单属性 = models.CharField(max_length=32)
    配送员 = models.CharField(max_length=32)
    推配送时间 = models.DateTimeField()
    骑手考核时间 = models.DateTimeField(null=True, blank=True)
    上报异常类型 = models.CharField(max_length=120, default="")
    备注信息 = models.CharField(max_length=120, default="")
    配送完成时间 = models.DateTimeField(null=True, blank=True)
    是否配送超时 = models.CharField(verbose_name="是否配送超时", max_length=4, default="")
    配送超时类型 = models.CharField(max_length=12, default="")

    class Meta:
        managed = True  # Django 不尝试创建或校验约束
        ordering = ("-推配送时间", "城市", "区域", "站点")
        unique_together = (("站点", "日期", "订单号"),)

    @staticmethod
    def 计算骑手送达(配送剩余时间, 骑手考核时间, use_str=True):
        if 配送剩余时间:
            a, b = 配送剩余时间.split()
            b = b.split(":")
            if len(b) == 3:
                v = int(b[-3]) * 60 * 60 + int(b[-2]) * 60 + int(b[-1])
            else:
                v = int(b[-2]) * 60 + int(b[-1])

            if a == "超":
                data_date = 骑手考核时间 + timedelta(seconds=v)
            elif a == "剩":
                data_date = 骑手考核时间 - timedelta(seconds=v)
            else:
                raise ValueError("未知的送达状态")

            return data_date.strftime("%Y-%m-%d %H:%M:%S") if use_str else data_date
        else:
            return None

    @staticmethod
    def 计算超时类型(配送剩余时间: str):
        if 配送剩余时间 and 配送剩余时间.startswith("超"):
            _, b = 配送剩余时间.split()
            b = b.split(":")
            if len(b) == 3:
                v = int(b[-3]) * 60 * 60 + int(b[-2]) * 60 + int(b[-1])
            else:
                v = int(b[-2]) * 60 + int(b[-1])

            if v >= 60 * 60:
                return "60+超时"
            elif v >= 60 * 30:
                return "30-60超时"
            elif v >= 60 * 10:
                return "10-30超时"
            else:
                return "普通超时"

        return ""


class 灯塔_订单_骑手(DateBaseModel):
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

    超时单量_普通超时 = models.IntegerField(verbose_name="超时单量_普通超时", default=0)
    超时单量_10_30超时 = models.IntegerField(verbose_name="超时单量_10-30超时", default=0)
    超时单量_30_60超时 = models.IntegerField(verbose_name="超时单量_30-60超时", default=0)
    超时单量_60_超时 = models.IntegerField(verbose_name="超时单量_60+超时", default=0)

    推配时段明细 = models.JSONField(verbose_name="推配时段", default=list)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点", "骑手mis号")
        unique_together = (("站点", "骑手姓名", "骑手mis号", "日期", "是否大网骑手"),)


class __灯塔_订单_城市区域站点(BaseModel):
    大网单量 = models.IntegerField(verbose_name="大网单量", default=0)
    推配完成单量 = models.IntegerField(verbose_name="推配完成单量", default=0)
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
    超时单量_普通超时 = models.IntegerField(verbose_name="超时单量_普通超时", default=0)
    超时单量_10_30超时 = models.IntegerField(verbose_name="超时单量_10-30超时", default=0)
    超时单量_30_60超时 = models.IntegerField(verbose_name="超时单量_30-60超时", default=0)
    超时单量_60_超时 = models.IntegerField(verbose_name="超时单量_60+超时", default=0)

    推配时段明细 = models.JSONField(verbose_name="推配时段", default=list)

    class Meta:
        abstract = True


class 灯塔_订单_站点(DateBaseModel, __灯塔_订单_城市区域站点):
    月工作日天数 = models.IntegerField(verbose_name="月工作日天数", default=0)
    月非工作日天数 = models.IntegerField(verbose_name="月非工作日天数", default=0)

    class Meta:
        ordering = ("-日期", "城市", "区域", "站点")
        unique_together = (("站点", "日期"),)


class 灯塔_订单_城市区域(__灯塔_订单_城市区域站点):
    class C_数据类别(models.TextChoices):
        商 = "商", "商"
        城市 = "城市", "城市"
        区域 = "区域", "区域"

    商 = models.CharField(max_length=8, default=COMPANY)
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

    数据类别 = models.CharField(verbose_name="数据类别", max_length=8, choices=C_数据类别.choices)

    class Meta:
        ordering = ("-日期", "城市", "区域")
        unique_together = (("商", "城市", "区域", "日期"),)


class 灯塔_订单_站点_时段数据(DateBaseModel):
    时段 = models.IntegerField(verbose_name="时段")

    完成单量 = models.IntegerField()
    超时单量 = models.IntegerField()
    准时率 = models.FloatField()
