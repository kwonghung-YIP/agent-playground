create table if not exists jobs (
    id uuid not null default gen_random_uuid() primary key,
    status varchar(30) not null,
    request JSONB,
    response JSONB
)