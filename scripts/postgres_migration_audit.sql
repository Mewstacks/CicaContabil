\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
\pset fieldsep '|'

SELECT format(
    'SELECT %L, count(*)::bigint FROM %I.%I;',
    schemaname || '.' || tablename,
    schemaname,
    tablename
)
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
\gexec

SELECT 'audit.invalid_indexes', count(*)::bigint
FROM pg_index
WHERE NOT indisvalid;

SELECT 'audit.unvalidated_constraints', count(*)::bigint
FROM pg_constraint
WHERE NOT convalidated;

SELECT 'audit.public_tables', count(*)::bigint
FROM pg_tables
WHERE schemaname = 'public';

SELECT 'audit.public_sequences', count(*)::bigint
FROM pg_sequences
WHERE schemaname = 'public';
