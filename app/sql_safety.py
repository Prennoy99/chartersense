"""Rejects any LLM-generated SQL that isn't a single, read-only SELECT
statement. This is a defense-in-depth check on top of the DB-level
protection (the query executes under chartersense_readonly, which only has
GRANT SELECT) — belt and suspenders, since the DB role alone can't stop a
multi-statement payload from at least attempting a write."""
import sqlparse
from sqlparse.tokens import CTE, DML

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "COPY", "CALL", "EXECUTE", "MERGE", "REPLACE",
}


class UnsafeSQLError(ValueError):
    pass


def validate_select_only(sql: str) -> str:
    """Raises UnsafeSQLError unless `sql` is exactly one read-only SELECT
    statement (a `WITH ... SELECT` CTE also qualifies). Returns the
    statement with any trailing semicolon stripped."""
    statements = [s for s in sqlparse.parse(sql) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        raise UnsafeSQLError(f"expected exactly one SQL statement, got {len(statements)}")

    stmt = statements[0]
    first_token = stmt.token_first(skip_cm=True)
    is_select = first_token is not None and first_token.ttype is DML and first_token.value.upper() == "SELECT"
    is_cte = first_token is not None and first_token.ttype is CTE and first_token.value.upper() == "WITH"
    if not (is_select or is_cte):
        raise UnsafeSQLError("only SELECT statements are allowed")

    # Backstop for CTEs in particular: Postgres allows a data-modifying
    # statement (INSERT/UPDATE/DELETE) as a CTE's final clause, e.g.
    # "WITH x AS (SELECT ...) DELETE FROM t ...". The keyword scan below
    # catches that even though the statement technically starts with WITH.
    upper_sql = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if kw in upper_sql:
            raise UnsafeSQLError(f"forbidden keyword detected: {kw}")

    return sql.strip().rstrip(";").strip()
