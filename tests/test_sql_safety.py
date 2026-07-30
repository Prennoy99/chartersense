import pytest

from app.sql_safety import UnsafeSQLError, validate_select_only


@pytest.mark.parametrize("sql", [
    "SELECT * FROM vessels;",
    "  select vessel_id, name from vessels WHERE vessel_type = 'Capesize'  ",
    "SELECT * FROM voyages WHERE charterer = (SELECT charterer FROM voyages LIMIT 1)",
    "WITH capesize AS (SELECT * FROM vessels WHERE vessel_type = 'Capesize') SELECT * FROM capesize",
    "SELECT count(*) FROM voyages",
])
def test_valid_select_statements_pass(sql):
    result = validate_select_only(sql)
    assert result  # non-empty
    assert not result.endswith(";")


@pytest.mark.parametrize("sql", [
    "DELETE FROM vessels",
    "UPDATE vessels SET name = 'x'",
    "INSERT INTO vessels VALUES (1)",
    "DROP TABLE vessels",
    "TRUNCATE vessels",
    "GRANT ALL ON vessels TO public",
])
def test_non_select_statements_rejected(sql):
    with pytest.raises(UnsafeSQLError):
        validate_select_only(sql)


def test_stacked_statement_injection_rejected():
    with pytest.raises(UnsafeSQLError, match="expected exactly one"):
        validate_select_only("SELECT * FROM vessels; DROP TABLE vessels;")


def test_select_with_forbidden_keyword_in_string_literal_still_rejected():
    # Defense-in-depth is keyword-based, not literal-aware — a SELECT that
    # merely mentions "DELETE" in a string is rejected too. Documents the
    # actual (conservative) behavior rather than a false claim of precision.
    with pytest.raises(UnsafeSQLError):
        validate_select_only("SELECT 'please DELETE this row' AS note")
