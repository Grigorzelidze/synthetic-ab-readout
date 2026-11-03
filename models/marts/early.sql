-- First 2000 user_id values. The cut is fixed in generate.py, not chosen after the metric.
select
    arm,
    count(*)::integer as n,
    sum(retained)::integer as n_retained
from {{ ref('unit') }}
where user_id < 2000
group by arm
