"""Typed tool definitions shared by the bounded Agent runtime."""

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    args_schema: type[BaseModel]
    handler: Callable[[BaseModel], dict]
