-- Booking/provider/payment workflow primitives.
-- Provider responses, payment recording, and final confirmation are transactional.
alter table public.bookings add column if not exists rejected_at timestamptz, add column if not exists rejection_reason text;
alter table public.properties add column if not exists availability_updated_at timestamptz;
alter table public.transactions add column if not exists paid_at timestamptz, add column if not exists failure_reason text;

create or replace function public.provider_booking_response(p_booking_id uuid,p_provider_user_id uuid,p_response text,p_provider_message text default null)
returns public.bookings language plpgsql security definer set search_path=public as $$
declare v_booking public.bookings%rowtype; v_provider_user uuid; v_new_status text;
begin
 if auth.uid() is null or auth.uid()<>p_provider_user_id then raise exception 'not authorized'; end if;
 select b.* into v_booking from public.bookings b where b.id=p_booking_id for update;
 if not found then raise exception 'booking not found'; end if;
 select user_id into v_provider_user from public.providers where id=v_booking.provider_id;
 if v_provider_user is null or v_provider_user<>p_provider_user_id then raise exception 'not authorized for provider'; end if;
 if v_booking.status not in ('pending','info_requested') then raise exception 'booking is not awaiting provider response'; end if;
 if lower(p_response) in ('confirm','confirmed','yes','accept','accepted') then
   update public.bookings set status='provider_accepted',provider_response=p_provider_message,updated_at=now() where id=p_booking_id returning * into v_booking;
 elsif lower(p_response) in ('reject','rejected','no','decline','declined') then
   update public.bookings set status='provider_declined',provider_response=p_provider_message,rejected_at=now(),rejection_reason=p_provider_message,updated_at=now() where id=p_booking_id returning * into v_booking;
 elsif lower(p_response) in ('info','question','more_info','additional_info') then
   update public.bookings set status='pending',provider_response=p_provider_message,additional_info_requested=jsonb_build_object('provider_message',p_provider_message,'requested_at',now()),updated_at=now() where id=p_booking_id returning * into v_booking;
 else raise exception 'unsupported provider response'; end if;
 return v_booking;
end; $$;

create or replace function public.confirm_booking_after_payment(p_booking_id uuid,p_transaction_id uuid)
returns public.bookings language plpgsql security definer set search_path=public as $$
declare v_booking public.bookings%rowtype; v_tx public.transactions%rowtype; v_remaining integer;
begin
 select * into v_booking from public.bookings where id=p_booking_id for update;
 if not found then raise exception 'booking not found'; end if;
 select * into v_tx from public.transactions where id=p_transaction_id and booking_id=p_booking_id for update;
 if not found or v_tx.status<>'successful' then raise exception 'successful payment required'; end if;
 if v_booking.status not in ('provider_accepted','confirmed') then raise exception 'booking is not accepted'; end if;
 if v_booking.status='confirmed' then return v_booking; end if;
 update public.bookings set status='confirmed',confirmed_at=now(),updated_at=now() where id=p_booking_id returning * into v_booking;
 update public.properties set available_rooms=greatest(coalesce(available_rooms,0)-1,0),availability_updated_at=now(),is_available=(greatest(coalesce(available_rooms,0)-1,0)>0),updated_at=now() where id=v_booking.property_id returning available_rooms into v_remaining;
 return v_booking;
end; $$;

create or replace function public.record_successful_payment(p_booking_id uuid,p_user_id uuid,p_amount numeric,p_currency text,p_provider_reference text,p_payment_method text,p_metadata jsonb default '{}'::jsonb)
returns uuid language plpgsql security definer set search_path=public as $$
declare v_booking public.bookings%rowtype; v_tx_id uuid;
begin
 if auth.uid() is null or auth.uid()<>p_user_id then raise exception 'not authorized'; end if;
 select * into v_booking from public.bookings where id=p_booking_id and user_id=p_user_id for update;
 if not found then raise exception 'booking not found'; end if;
 if v_booking.status not in ('provider_accepted','pending') then raise exception 'booking not payable in current state'; end if;
 insert into public.transactions(booking_id,user_id,amount,currency,provider_reference,payment_method,status,paid_at,metadata)
 values(p_booking_id,p_user_id,p_amount,p_currency,p_provider_reference,p_payment_method,'successful',now(),p_metadata) returning id into v_tx_id;
 return v_tx_id;
end; $$;

grant execute on function public.provider_booking_response(uuid,uuid,text,text) to authenticated;
grant execute on function public.confirm_booking_after_payment(uuid,uuid) to authenticated;
grant execute on function public.record_successful_payment(uuid,uuid,numeric,text,text,text,jsonb) to authenticated;
