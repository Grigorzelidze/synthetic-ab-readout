select
    arm,
    count(*)::integer as n,
    sum(retained)::integer as n_retained,
    avg(revenue)::float8 as mean_revenue,
    stddev_samp(revenue)::float8 as sd_revenue
from {{ ref('unit') }}
group by arm
