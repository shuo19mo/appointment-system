from enum import StrEnum


class TaskType(StrEnum):
    SCHEDULING = "scheduling"
    CONSULTATION = "consultation"
    UNRELATED = "unrelated"


ACTIVE_BOOKING_STATUSES = ("confirmed", "pending")
DEFAULT_TIMEZONE = "Asia/Shanghai"
