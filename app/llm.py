"""LLM grounding: natural-language question -> SQL, and results -> plain-English
answer. Grounded in semantic_layer/metrics.yaml, not the raw table schema —
that grounding is the actual point of the project."""
import os
from pathlib import Path

from google import genai

SEMANTIC_LAYER_PATH = Path(__file__).resolve().parent.parent / "semantic_layer" / "metrics.yaml"

# The semantic layer's metric formulas already reference qualified column
# names (e.g. "voyages.cargo_quantity_tons"), so pasting it in doubles as
# schema grounding for the columns it uses. What it doesn't spell out is
# join keys and a couple of column-format notes, filled in here.
SCHEMA_NOTES = """
Table relationships:
  vessels.vessel_id  <-  voyages.vessel_id        (FK)
  voyages.voyage_id  <-  voyage_costs.voyage_id    (FK, 1:1)
  freight_rates is NOT joined to voyages — it is an independent market-rate
  series (route/date/vessel_type) used only for avg_freight_rate_by_route.

Column notes:
  route (as used in freight_rates.route) = voyages.load_port || '-' || voyages.discharge_port
  All monetary columns are USD. All *_days columns are NUMERIC, not integer.
  voyages.commencement_date is the date to filter on for "last month" / "last quarter" / date-range questions.
"""

SQL_RULES = """
Rules:
- Output ONLY a single PostgreSQL SELECT statement. No prose, no markdown code fences, no explanation.
- Use only the metric formulas, tables, and columns referenced in the semantic layer above — do not invent your own definition for a metric that's already defined there.
- Never use INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE or any statement other than SELECT.
- Give result columns explicit, self-describing aliases (e.g. AS avg_tce_usd_per_day).
- Today's date is {today}, if you need it to resolve a relative date range.
"""


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not set. Get a free-tier key at https://aistudio.google.com/apikey "
            "and add it to .env as GEMINI_API_KEY=..."
        )
    return genai.Client(api_key=api_key)


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def _sql_system_prompt(today: str) -> str:
    semantic_layer_yaml = SEMANTIC_LAYER_PATH.read_text()
    return (
        "You are a SQL generator for CharterSense, a dry-bulk shipping analytics system.\n"
        "Ground every answer in the semantic layer below — use its exact formulas and column\n"
        "references rather than inventing your own business logic.\n\n"
        "SEMANTIC LAYER:\n"
        f"{semantic_layer_yaml}\n"
        f"{SCHEMA_NOTES}\n"
        f"{SQL_RULES.format(today=today)}"
    )


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("sql"):
            text = text[3:]
    return text.strip()


def generate_sql(question: str, today: str) -> str:
    client = _client()
    response = client.models.generate_content(
        model=_model_name(),
        contents=f"{_sql_system_prompt(today)}\n\nQuestion: {question}\n\nSQL:",
    )
    return _strip_code_fence(response.text)


def explain_answer(question: str, sql: str, columns: list[str], rows: list[list]) -> str:
    client = _client()
    prompt = (
        "You answered a business question by running SQL against CharterSense's dry-bulk\n"
        "chartering database. Write a short, plain-English answer (1-3 sentences) using the\n"
        "query results below. Cite the actual numbers. Do not restate or explain the SQL.\n\n"
        f"Question: {question}\n"
        f"Result columns: {columns}\n"
        f"Result rows: {rows}\n"
    )
    response = client.models.generate_content(model=_model_name(), contents=prompt)
    return response.text.strip()
