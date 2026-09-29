-- Public, local-demo-only credentials. No database port is exposed by Compose.
CREATE ROLE appwriter LOGIN PASSWORD 'local-demo-writer-only' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE appreader LOGIN PASSWORD 'local-demo-reader-only' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT ON DATABASE marketreadiness TO appwriter, appreader;
GRANT USAGE, CREATE ON SCHEMA public TO appwriter;
GRANT USAGE ON SCHEMA public TO appreader;
ALTER DEFAULT PRIVILEGES FOR ROLE appwriter IN SCHEMA public GRANT SELECT ON TABLES TO appreader;
ALTER ROLE appreader SET default_transaction_read_only = on;
