"""Postgres connection helper, shared by the validation module and (later)
the FastAPI backend."""
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection(readonly: bool = True):
    """Connect to the CharterSense DB.

    readonly=True (the default) uses the chartersense_readonly role, which
    only has GRANT SELECT — this is the role any LLM-generated SQL must run
    under (Milestone 3). readonly=False uses the admin role and should only
    be used by seeding/schema code, never by query-answering code paths.
    """
    if readonly:
        user = os.getenv("POSTGRES_READONLY_USER", "chartersense_readonly")
        password = os.getenv("POSTGRES_READONLY_PASSWORD", "readonly_pw")
    else:
        user = os.getenv("POSTGRES_USER", "chartersense_admin")
        password = os.getenv("POSTGRES_PASSWORD", "admin_pw")

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "chartersense"),
        user=user,
        password=password,
    )
