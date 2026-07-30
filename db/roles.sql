-- Read-only role that the LLM-generated SQL executes against.
-- SELECT only, never write/delete access.

CREATE ROLE chartersense_readonly LOGIN PASSWORD 'readonly_pw';

GRANT CONNECT ON DATABASE chartersense TO chartersense_readonly;
GRANT USAGE ON SCHEMA public TO chartersense_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO chartersense_readonly;

-- Any tables created later by the owner role also get SELECT-only access.
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO chartersense_readonly;
