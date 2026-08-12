import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const webhookSecret = Deno.env.get("PAYMENT_WEBHOOK_SECRET");

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  if (webhookSecret && req.headers.get("x-webhook-secret") !== webhookSecret) return new Response("Unauthorized", { status: 401 });
  const body = await req.json().catch(() => null);
  if (!body) return new Response("Bad request", { status: 400 });
  const bookingId = body.booking_id;
  const reference = body.provider_reference ?? body.reference;
  const status = String(body.status ?? "").toLowerCase();
  if (!bookingId || !reference || !status) return new Response("Missing payment fields", { status: 400 });
  const { data: booking } = await supabase.from("bookings").select("id,user_id,price_amount").eq("id", bookingId).maybeSingle();
  if (!booking) return new Response("Booking not found", { status: 404 });
  const amount = Number(body.amount ?? booking.price_amount);
  const currency = body.currency ?? "USD";
  if (status !== "successful") {
    await supabase.from("transactions").insert({ booking_id: bookingId, user_id: booking.user_id, amount, currency, provider_reference: reference, status: "failed", failure_reason: body.failure_reason ?? null, metadata: body });
    return Response.json({ recorded: true, status: "failed" });
  }
  const { data: existing } = await supabase.from("transactions").select("id").eq("provider_reference", reference).maybeSingle();
  if (existing) return Response.json({ recorded: true, duplicate: true });
  const { data: tx, error } = await supabase.from("transactions").insert({ booking_id: bookingId, user_id: booking.user_id, amount, currency, provider_reference: reference, status: "successful", paid_at: new Date().toISOString(), metadata: body }).select("id").single();
  if (error || !tx) return new Response("Could not record transaction", { status: 500 });
  const { error: confirmationError } = await supabase.rpc("confirm_booking_after_payment", { p_booking_id: bookingId, p_transaction_id: tx.id });
  if (confirmationError) return Response.json({ recorded: true, confirmed: false, error: confirmationError.message }, { status: 409 });
  return Response.json({ recorded: true, confirmed: true });
});
