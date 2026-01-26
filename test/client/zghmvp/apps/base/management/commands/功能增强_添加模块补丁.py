# core
import typing
from typing import cast

from django.core.management.base import BaseCommand
from patchright.async_api import ElementHandle, Page

from zghmvp.tools.patcher import ASTMethodInjector


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with ASTMethodInjector() as ast:
            ast.add_import(Page, [cast])

            # @ast.add(Page, replace=True)
            # async def query_selector(self: "Page", selector: str) -> typing.Optional["ElementHandle"]:
            #     el_top: typing.Optional["ElementHandle"] = await self.wait_for_selector(selector="html", state="attached", timeout=1000 * 30)
            #     if not el_top:
            #         raise TimeoutError(f"未找到元素: {selector}")
            #     else:
            #         return await el_top.query_selector(selector)

            # @ast.add(Page, replace=True)
            # async def query_selector_all(self: "Page", selector: str) -> list["ElementHandle"]:
            #     el_top: typing.Optional["ElementHandle"] = await self.wait_for_selector(selector="html", state="attached", timeout=1000 * 30)
            #     if not el_top:
            #         raise TimeoutError(f"未找到元素: {selector}")
            #     else:
            #         return await el_top.query_selector_all(selector=selector)

            @ast.add(Page, replace=True)
            async def wait_element(
                self: "Page",
                selector: str,
                timeout: float | None = None,
                state: typing.Literal["attached", "detached", "hidden", "visible"] = "visible",
            ) -> "ElementHandle":  # noqa: F811
                """等待元素可见后点击"""
                el: typing.Optional["ElementHandle"] = await self.wait_for_selector(selector, state=state, timeout=timeout)
                if not el:
                    raise TimeoutError(f"未找到元素: {selector}")
                else:
                    return el

            @ast.add(Page, replace=True)
            async def wait_and_click(self: "Page", selector: str, timeout: float | None = None) -> "ElementHandle":  # noqa: F811
                """等待元素可见后点击"""
                el: "ElementHandle" = await self.wait_element(selector, timeout=timeout)  # type: ignore
                await el.click()
                return el

            @ast.add(Page, replace=True)
            async def wait_and_fill(self: "Page", selector: str, value: str, timeout: float | None = None) -> "ElementHandle":  # noqa: F811
                """等待元素可见后填充文本"""
                el: "ElementHandle" = await self.wait_element(selector, timeout=timeout)  # type: ignore
                await el.fill(value)
                return el

            @ast.add(ElementHandle, replace=True)
            async def wait_element(
                self: "ElementHandle",
                selector: str,
                timeout: float | None = None,
                state: typing.Literal["attached", "detached", "hidden", "visible"] = "visible",
            ) -> "ElementHandle":  # noqa: F811
                """等待元素可见后点击"""
                el: typing.Optional["ElementHandle"] = await self.wait_for_selector(selector, state=state, timeout=timeout)
                if not el:
                    raise TimeoutError(f"未找到元素: {selector}")
                else:
                    return el

            @ast.add(ElementHandle, replace=True)
            async def wait_and_click(self: "ElementHandle", selector: str, timeout: float | None = None) -> "ElementHandle":
                """等待元素可见后点击"""
                el: "ElementHandle" = await self.wait_element(selector, timeout=timeout)  # type: ignore
                await el.click()
                return el

            @ast.add(ElementHandle, replace=True)
            async def wait_and_fill(self: "ElementHandle", selector: str, value: str, timeout: float | None = None) -> "ElementHandle":
                """等待元素可见后填充文本"""
                el: "ElementHandle" = await self.wait_element(selector, timeout=timeout)  # type: ignore
                await el.fill(value)
                return el
