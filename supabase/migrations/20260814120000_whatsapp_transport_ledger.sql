create extension if not exists pgcrypto;

create table if not exists public.whatsapp_events (
  id uuid primary key default gen_random_uuid(),
  event_key text not null unique,
  event_type text not null check (event_type in ('message', 'status')),
  meta_message_id text,
  payload jsonb not null,
  processing_status text not null default 'received'
    check (processing_status in ('received', 'processed', 'failed')),
  processing_error text,
  received_at timestamptz not null default now(),
  processed_at timestamptz
);

create index if not exists whatsapp_events_meta_message_id_idx on public.whatsapp_events(meta_message_id);
create index if not exists whatsapp_events_status_idx on public.whatsapp_events(processing_status, received_at);

create table if not exists public.whatsapp_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references public.conversations(id) on delete set null,
  meta_message_id text unique,
  direction text not null check (direction in ('inbound', 'outbound')),
  phone_number text not null,
  message_type text not null,
  body text,
  status text not null default 'received' check (status in ('received', 'queued', 'sent', 'delivered', 'read', 'failed')),
  metadata jsonb not null default '{}'::jsonb,
  error_code text,
  error_message text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  delivered_at timestamptz,
  read_at timestamptz,
  failed_at timestamptz
);

create index if not exists whatsapp_messages_phone_idx on public.whatsapp_messages(phone_number, created_at desc);
create index if not exists whatsapp_messages_status_idx on public.whatsapp_messages(status, created_at desc);

alter table public.whatsapp_events enable row level security;
alter table public.whatsapp_messages enable row level security;
revoke all on public.whatsapp_events from anon, authenticated;
revoke all on public.whatsapp_messages from anon, authenticated;
