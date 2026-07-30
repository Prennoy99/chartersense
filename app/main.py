"""Milestone 3: POST /query takes a plain-English question, grounds an LLM in
semantic_layer/metrics.yaml, generates SQL, validates it's read-only, executes
it against the read-only DB role, and returns a plain-English answer.

Milestone 4: serves the static chat UI (app/static/index.html) at "/". The
StaticFiles mount is registered last so it doesn't shadow /health or /query —
Starlette matches routes in registration order."""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.db import get_connection
from app.llm import explain_answer, generate_sql
from app.schemas import QueryRequest, QueryResponse
from app.sql_safety import UnsafeSQLError, validate_select_only

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CharterSense")


def _jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    raw_sql = generate_sql(req.question, today=date.today().isoformat())

    try:
        safe_sql = validate_select_only(raw_sql)
    except UnsafeSQLError as e:
        raise HTTPException(
            status_code=400,
            detail=f"generated SQL rejected ({e}). SQL was: {raw_sql}",
        )

    try:
        with get_connection(readonly=True) as conn, conn.cursor() as cur:
            cur.execute(safe_sql)
            columns = [desc[0] for desc in cur.description]
            rows = [[_jsonable(v) for v in row] for row in cur.fetchall()]
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"generated SQL failed to execute: {e}. SQL was: {safe_sql}",
        )

    answer = explain_answer(req.question, safe_sql, columns, rows)

    return QueryResponse(
        question=req.question,
        sql=safe_sql,
        columns=columns,
        rows=rows,
        answer=answer,
    )


# Registered last so it never shadows /health or /query.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
