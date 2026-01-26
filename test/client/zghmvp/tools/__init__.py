# core

from datetime import date, datetime
from functools import cache
from typing import Callable, TypeVar

from chinese_calendar import is_workday
from typing_extensions import ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def typed_cache(func: Callable[P, R]) -> Callable[P, R]:
    """A type-safe version of functools.cache."""
    return cache(func)  # type: ignore


@typed_cache
def is_workday_cache(date: date | datetime) -> bool:
    return is_workday(date)
