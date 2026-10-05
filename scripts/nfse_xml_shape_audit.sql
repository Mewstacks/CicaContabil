\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
\pset fieldsep '|'

WITH tags AS (
    SELECT (
        regexp_matches(
            original_xml,
            '<(?:[[:alnum:]_.-]+:)?([[:alpha:]_][[:alnum:]_.-]*)[[:space:]/>]',
            'g'
        )
    )[1] AS tag
    FROM hub_nfsedocument
)
SELECT tag, count(*)::bigint
FROM tags
GROUP BY tag
ORDER BY count(*) DESC, tag
LIMIT 80;

SELECT
    'xml_lengths',
    min(length(original_xml)),
    max(length(original_xml)),
    min(ascii(substr(original_xml, 1, 1))),
    max(ascii(substr(original_xml, 1, 1)))
FROM hub_nfsedocument;

SELECT key, count(*)::bigint
FROM hub_nfsedocument
CROSS JOIN LATERAL jsonb_object_keys(normalized_data) AS key
GROUP BY key
ORDER BY count(*) DESC, key;
