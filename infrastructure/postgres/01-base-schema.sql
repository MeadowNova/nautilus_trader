\echo 'Loading Nautilus Trader base schema...'

-- Mount `schema/sql` into /docker-entrypoint-initdb.d/schema via docker-compose.
\i /docker-entrypoint-initdb.d/schema/types.sql
\i /docker-entrypoint-initdb.d/schema/tables.sql
\i /docker-entrypoint-initdb.d/schema/functions.sql
\i /docker-entrypoint-initdb.d/schema/partitions.sql

\echo 'Base schema loaded.'
