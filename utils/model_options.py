"""模型升級時保留既有推理模式，避免依賴供應商的預設值。"""
from typing import Literal, TypedDict


class ReasoningOptions(TypedDict, total=False):
    reasoning_effort: Literal["none"]


def reasoning_options(model: str) -> ReasoningOptions:
    # Luna / Sol 預設 medium；原 5.4 / nano 預設 none。
    # Chat Completions 的 Luna 工具呼叫也需要 none。
    if model in {"gpt-6-luna", "gpt-6-sol"}:
        return {"reasoning_effort": "none"}
    return {}
