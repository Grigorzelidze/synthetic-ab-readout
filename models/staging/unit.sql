select
    user_id::integer as user_id,
    arm,
    retained::integer as retained,
    revenue::numeric as revenue
from {{ source('raw_src', 'unit') }}
