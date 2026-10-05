\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
\pset fieldsep '|'

SELECT format(
    'SELECT %L, count(*)::bigint, md5(COALESCE(string_agg(row_hash, '''' ORDER BY row_hash), '''')) FROM (SELECT md5(row_to_json(t)::text) AS row_hash FROM %I.%I AS t) AS rows;',
    schemaname || '.' || tablename,
    schemaname,
    tablename
)
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
\gexec
