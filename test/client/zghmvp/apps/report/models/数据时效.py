# core
import time

from django.db import models

from zghmvp.tools.models import BaseModel


class 数据时效(BaseModel):
    name = models.CharField(max_length=64)
    time = models.FloatField(default=0)
    valid_time = models.FloatField(default=0)

    @classmethod
    def is_valid(cls, name: str, valid_time: float = 0):
        model = cls.objects.filter(name=name).first()
        if model:
            valid_time = valid_time if valid_time > 0 else model.valid_time
            return (time.time() - model.time) > valid_time
        else:
            return True

    @classmethod
    def update_valid_time(cls, name: str, valid_time: float):
        model, _ = cls.objects.get_or_create(name=name, defaults={"time": 0, "valid_time": 0})
        model.time = time.time()
        model.valid_time = valid_time
        model.save()

    class Meta:
        ordering = ("-time", "name")
        unique_together = (("name",),)
