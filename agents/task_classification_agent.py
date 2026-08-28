"""Deterministic task router; a model can be layered on without changing callers."""

import re


class TaskClassificationAgent:
    SCHEDULING_TERMS = ("约课", "预约课程", "安排课程", "排课", "上课时间", "档期", "老师有空", "改期", "取消课程", "确认", "改成", "分钟")
    CONSULTATION_TERMS = ("课程", "校区", "地址", "政策", "适合", "教什么", "怎么学", "老师介绍", "费用")

    def classify(self, text: str) -> str:
        normalized = (text or "").strip()
        if any(term in normalized for term in ("多少钱", "费用", "价格", "收费")):
            return "consultation"
        if any(term in normalized for term in self.SCHEDULING_TERMS):
            return "scheduling"
        if re.search(r"(?:给|帮|想|要|安排).{0,30}约", normalized) or normalized.startswith("约"):
            return "scheduling"
        if any(term in normalized for term in self.CONSULTATION_TERMS):
            return "consultation"
        return "unrelated"
