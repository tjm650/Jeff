-- Align the initial Supabase foundation with the fields and invariants
-- currently present in the legacy Django models.

alter table public.providers
  add column if not exists verified boolean not null default false,
  add column if not exists rating numeric(3,2) not null default 0 check (rating between 0 and 5),
  add column if not exists total_reviews integer not null default 0 check (total_reviews >= 0);

alter table public.properties
  add column if not exists property_no text unique,
  add column if not exists total_rooms integer,
  add column if not exists available_rooms integer,
  add column if not exists available_1h_rooms integer not null default 0,
  add column if not exists available_2h_rooms integer not null default 0,
  add column if not exists available_3h_rooms integer not null default 0,
  add column if not exists available_4h_rooms integer not null default 0,
  add column if not exists amenities jsonb not null default '[]'::jsonb,
  add column if not exists price_per_semester numeric(12,2),
  add column if not exists price_per_month numeric(12,2),
  add column if not exists price_per_week numeric(12,2),
  add column if not exists price_per_day numeric(12,2),
  add column if not exists distance_from_campus numeric(10,3),
  add column if not exists campus_name text,
  add column if not exists gender_preference text not null default 'any' check (gender_preference in ('male','female','any','mixed')),
  add column if not exists rating numeric(3,2) not null default 0 check (rating between 0 and 5),
  add column if not exists total_reviews integer not null default 0 check (total_reviews >= 0);

create index if not exists properties_property_no_idx on public.properties(property_no);
create index if not exists properties_campus_available_idx on public.properties(campus_name, available_rooms);
create index if not exists properties_gender_idx on public.properties(gender_preference);
create index if not exists properties_price_month_idx on public.properties(price_per_month);
create index if not exists properties_distance_idx on public.properties(distance_from_campus);
create index if not exists properties_rating_idx on public.properties(rating);

alter table public.entitlements
  add column if not exists source_transaction_id uuid references public.transactions(id) on delete set null;

create table public.token_uses (
  id uuid primary key default gen_random_uuid(),
  entitlement_id uuid not null references public.entitlements(id) on delete cascade,
  user_id uuid not null references public.profiles(id) on delete cascade,
  used_at timestamptz not null default now(),
  context jsonb not null default '{}'::jsonb
);

create index token_uses_entitlement_idx on public.token_uses(entitlement_id, used_at);
create index token_uses_user_idx on public.token_uses(user_id, used_at);
alter table public.token_uses enable row level security;
create policy token_uses_own on public.token_uses for select to authenticated using (user_id = auth.uid());

alter table public.transactions
  add column if not exists transaction_number text unique,
  add column if not exists payment_method text,
  add column if not exists pop_path text,
  add column if not exists pop_verified boolean not null default false,
  add column if not exists verified_at timestamptz;

create index if not exists transactions_transaction_number_idx on public.transactions(transaction_number);

alter table public.bookings
  add column if not exists booking_number text unique,
  add column if not exists rental_period text not null default 'month' check (rental_period in ('day','week','month')),
  add column if not exists price_amount numeric(12,2) not null default 0,
  add column if not exists provider_response text,
  add column if not exists additional_info_requested jsonb not null default '{}'::jsonb,
  add column if not exists confirmed_at timestamptz;

create index if not exists bookings_booking_number_idx on public.bookings(booking_number);

alter table public.conversations
  add column if not exists selected_properties jsonb not null default '[]'::jsonb,
  add column if not exists last_message_at timestamptz not null default now();

alter table public.reviews
  add column if not exists cell_number text;

create unique index if not exists reviews_user_property_unique
  on public.reviews(user_id, property_id)
  where user_id is not null;

create table public.conversation_security_events (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references public.conversations(id) on delete cascade,
  phone_number text,
  agent_id text,
  message_count integer not null default 0,
  is_suspicious boolean not null default false,
  flagged_reason text,
  occurred_at timestamptz not null default now()
);

create index conversation_security_events_conversation_idx on public.conversation_security_events(conversation_id);
create index conversation_security_events_suspicious_idx on public.conversation_security_events(is_suspicious);
alter table public.conversation_security_events enable row level security;

create or replace view public.property_search_summary as
select
  p.id,
  p.property_no,
  p.provider_id,
  p.name,
  p.address,
  p.description,
  p.amenities,
  p.total_rooms,
  p.available_rooms,
  p.available_1h_rooms,
  p.available_2h_rooms,
  p.available_3h_rooms,
  p.available_4h_rooms,
  p.price_per_semester,
  p.price_per_month,
  p.price_per_week,
  p.price_per_day,
  p.distance_from_campus,
  p.campus_name,
  p.gender_preference,
  p.rating,
  p.total_reviews,
  p.is_available,
  p.created_at,
  p.updated_at
from public.properties p
where p.is_available = true;
