from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


async def list_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str | None = None,
    goal_id: uuid.UUID | None = None,
    due_from: datetime | None = None,
    due_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> tuple[list[Task], str | None]:
    q = select(Task).where(Task.user_id == user_id, Task.deleted == False)  # noqa: E712
    if status:
        q = q.where(Task.status == status)
    if goal_id:
        q = q.where(Task.goal_id == goal_id)
    if due_from:
        q = q.where(Task.due_at >= due_from)
    if due_to:
        q = q.where(Task.due_at <= due_to)

    # cursor-based on updated_at+id for MVP
    if cursor:
        try:
            ts_str, id_str = cursor.split("|")
            ts = datetime.fromisoformat(ts_str)
            cid = uuid.UUID(id_str)
            q = q.where((Task.updated_at, Task.id) < (ts, cid))
        except Exception:
            pass

    q = q.order_by(Task.updated_at.desc(), Task.id.desc()).limit(max(1, min(limit, 100)) + 1)
    res = await db.execute(q)
    rows = res.scalars().all()

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = f"{last.updated_at.isoformat()}|{last.id}"
        rows = rows[:limit]

    return rows, next_cursor


async def create_task(db: AsyncSession, user_id: uuid.UUID, data: dict) -> Task:
    now = datetime.now(timezone.utc)
    task = Task(
        user_id=user_id,
        title=data["title"],
        description=data.get("description"),
        goal_id=data.get("goal_id"),
        due_at=data.get("due_at"),
        priority=data.get("priority"),
        estimated_minutes=data.get("estimated_minutes"),
        energy_level=data.get("energy_level"),
        status="todo",
        created_at=now,
        updated_at=now,
        deleted=False,
    )
    db.add(task)
    await db.flush()
    return task


async def update_task(db: AsyncSession, task: Task, patch: dict, expected_updated_at: datetime | None) -> Task:
    if expected_updated_at and task.updated_at.replace(tzinfo=timezone.utc) != expected_updated_at.replace(tzinfo=timezone.utc):
        # conflict
        raise ValueError("conflict")

    values = {k: v for k, v in patch.items() if v is not None and k not in {"request_id", "updated_at"}}
    values["updated_at"] = datetime.now(timezone.utc)

    await db.execute(update(Task).where(Task.id == task.id).values(**values))
    await db.refresh(task)
    return task


async def soft_delete_task(db: AsyncSession, task: Task) -> Task:
    await db.execute(update(Task).where(Task.id == task.id).values(deleted=True, updated_at=datetime.now(timezone.utc)))
    await db.refresh(task)
    return task
