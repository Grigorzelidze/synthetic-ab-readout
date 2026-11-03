-- Chi-square, 1 df, critical value 10.827 is the 0.001 point.
-- A fair 50/50 split of this file stays under it. A 10% hole in treatment does not.
with counts as (
    select
        count(*) filter (where arm = 'control')::numeric as n0,
        count(*) filter (where arm = 'treatment')::numeric as n1
    from {{ ref('unit') }}
)
select n0, n1
from counts
where (power(n0 - (n0 + n1) / 2, 2) + power(n1 - (n0 + n1) / 2, 2))
    / ((n0 + n1) / 2) > 10.827
