from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TaskOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    status: str
    priority: int | None = None
    estimated_minutes: int | None = None
    energy_level: int | None = None
    goal_id: uuid.UUID | None = None
    due_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted: bool = False

    class Config:
        from_attributes = True


class TaskCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    goal_id: uuid.UUID | None = None
    due_at: datetime | None = None
    priority: int | None = None
    estimated_minutes: int | None = None
    energy_level: int | None = None
    request_id: str


class TaskUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    goal_id: uuid.UUID | None = None
    due_at: datetime | None = None
    priority: int | None = None
    estimated_minutes: int | None = None
    energy_level: int | None = None
    status: str | None = None
    updated_at: datetime | None = None
    request_id: str


class TaskDeleteIn(BaseModel):
    request_id: str


class TaskListOut(BaseModel):
    items: list[TaskOut]
    next_cursor: str | None = None
    request_id: str
