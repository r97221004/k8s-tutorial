from fastapi import APIRouter, HTTPException, status

from ..database import get_connection
from ..schemas import Todo, TodoCreate, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


def _row_to_todo(row) -> Todo:
    return Todo(
        id=row["id"],
        title=row["title"],
        completed=bool(row["completed"]),
        created_at=row["created_at"],
    )


@router.get("", response_model=list[Todo])
async def list_todos() -> list[Todo]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, completed, created_at FROM todos ORDER BY id DESC"
        ).fetchall()
    return [_row_to_todo(row) for row in rows]


@router.post("", response_model=Todo, status_code=status.HTTP_201_CREATED)
async def create_todo(payload: TodoCreate) -> Todo:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")

    with get_connection() as connection:
        cursor = connection.execute("INSERT INTO todos (title) VALUES (?)", (title,))
        row = connection.execute(
            "SELECT id, title, completed, created_at FROM todos WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    return _row_to_todo(row)


@router.patch("/{todo_id}", response_model=Todo)
async def update_todo(todo_id: int, payload: TodoUpdate) -> Todo:
    updates: list[str] = []
    values: list[object] = []

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        updates.append("title = ?")
        values.append(title)

    if payload.completed is not None:
        updates.append("completed = ?")
        values.append(1 if payload.completed else 0)

    if updates:
        values.append(todo_id)
        with get_connection() as connection:
            cursor = connection.execute(
                f"UPDATE todos SET {', '.join(updates)} WHERE id = ?", values
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Todo not found")
            row = connection.execute(
                "SELECT id, title, completed, created_at FROM todos WHERE id = ?",
                (todo_id,),
            ).fetchone()
    else:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT id, title, completed, created_at FROM todos WHERE id = ?",
                (todo_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Todo not found")

    return _row_to_todo(row)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: int) -> None:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Todo not found")
