-- Transactional primitives for the migrated Jeff conversation workflow.
-- Keep privileged mutations server-side; clients should use RLS-safe reads.

create or replace function public.consume_search_entitlement(p_user_id uuid, p_context jsonb default '{}'::jsonb)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_entitlement public.entitlements%rowtype;
  v_use_id uuid;
begin
  if auth.uid() is null or auth.uid() <> p_user_id then
    raise exception 'not authorized';
  end if;

  select * into v_entitlement
  from public.entitlements
  where user_id = p_user_id
    and token_type = 'search'
    and quantity > 0
    and (expires_at is null or expires_at > now())
  order by expires_at nulls last, created_at
  for update skip locked
  limit 1;

  if not found then
    raise exception 'no search entitlement available';
  end if;

  update public.entitlements
  set quantity = quantity - 1, updated_at = now()
  where id = v_entitlement.id;

  insert into public.token_uses(entitlement_id, user_id, context)
  values (v_entitlement.id, p_user_id, p_context)
  returning id into v_use_id;

  return v_use_id;
end;
$$;

create or replace function public.create_booking_request(
  p_conversation_id uuid,
  p_property_id uuid,
  p_guest_name text,
  p_guest_phone text,
  p_start_date date,
  p_end_date date,
  p_rental_period text,
  p_price_amount numeric,
  p_notes text default null
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_provider_id uuid;
  v_booking_id uuid;
begin
  select user_id into v_user_id from public.conversations where id = p_conversation_id;
  if v_user_id is null or auth.uid() is null or auth.uid() <> v_user_id then
    raise exception 'not authorized';
  end if;

  select provider_id into v_provider_id from public.properties where id = p_property_id and is_available = true;
  if v_provider_id is null then
    raise exception 'property unavailable';
  end if;

  insert into public.bookings(
    conversation_id, user_id, property_id, provider_id, guest_name, guest_phone,
    start_date, end_date, rental_period, price_amount, notes, status
  ) values (
    p_conversation_id, v_user_id, p_property_id, v_provider_id, p_guest_name, p_guest_phone,
    p_start_date, p_end_date, p_rental_period, p_price_amount, p_notes, 'pending'
  ) returning id into v_booking_id;

  update public.conversations
  set current_step = 'booking_request', updated_at = now(), last_message_at = now()
  where id = p_conversation_id;

  return v_booking_id;
end;
$$;

create or replace function public.append_conversation_message(
  p_conversation_id uuid,
  p_sender_type text,
  p_message text,
  p_media_url text default null,
  p_metadata jsonb default '{}'::jsonb
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user_id uuid;
  v_message_id uuid;
begin
  select user_id into v_user_id from public.conversations where id = p_conversation_id;
  if auth.uid() is null or auth.uid() <> v_user_id then
    raise exception 'not authorized';
  end if;

  insert into public.conversation_messages(conversation_id, sender_type, message, media_url, metadata)
  values (p_conversation_id, p_sender_type, p_message, p_media_url, p_metadata)
  returning id into v_message_id;

  update public.conversations
  set last_message_at = now(), updated_at = now()
  where id = p_conversation_id;

  return v_message_id;
end;
$$;

revoke all on function public.consume_search_entitlement(uuid, jsonb) from public;
grant execute on function public.consume_search_entitlement(uuid, jsonb) to authenticated;
revoke all on function public.create_booking_request(uuid, uuid, text, text, date, date, text, numeric, text) from public;
grant execute on function public.create_booking_request(uuid, uuid, text, text, date, date, text, numeric, text) to authenticated;
revoke all on function public.append_conversation_message(uuid, text, text, text, jsonb) from public;
grant execute on function public.append_conversation_message(uuid, text, text, text, jsonb) to authenticated;
