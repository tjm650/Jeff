import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);

function classify(text: string) {
  const t = text.trim().toLowerCase();
  if (/^(hi|hello|hey|good morning|good afternoon|good evening)\b/.test(t)) return "G";
  if (/\b(help|how do i|what can you do)\b/.test(t)) return "H";
  if (/\b(about jeff|who are you|what is jeff)\b/.test(t)) return "J";
  if (/\b(restart|reset|start over|cancel)\b/.test(t)) return "X";
  if (/\b(pay|payment|paid|proof of payment)\b/.test(t)) return "P";
  if (/^(option|select|property)\s*[-#]?\s*\d+/i.test(t)) return "S";
  if (/^(my name is|name is|i am|i'm)\b/.test(t)) return "N";
  return "A";
}

function extractRequirements(text: string) {
  const t = text.toLowerCase();
  const heads = Number(t.match(/\b([1-4])\s*(?:bed|bedroom|person|people|room)/)?.[1] ?? NaN);
  const budget = Number(t.match(/(?:\$|usd\s*)(\d+(?:\.\d+)?)/)?.[1] ?? NaN);
  const rental_period = /\b(day|daily)\b/.test(t) ? "day" : /\b(week|weekly)\b/.test(t) ? "week" : "month";
  const gender_preference = /\b(female|women|ladies)\b/.test(t) ? "female" : /\b(male|men)\b/.test(t) ? "male" : null;
  const distance_preference = /\b(near|close|nearby)\b/.test(t) ? "near" : /\b(far|away)\b/.test(t) ? "far" : null;
  return { heads: Number.isFinite(heads) ? heads : null, budget_max: Number.isFinite(budget) ? budget : null, rental_period, gender_preference, distance_preference };
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const body = await req.json().catch(() => null);
  const phone = body?.phone_number;
  const text = body?.message;
  if (!phone || typeof text !== "string") return Response.json({ error: "phone_number and message are required" }, { status: 400 });

  const classification = classify(text);
  let { data: conversation } = await db.from("conversations").select("*").eq("phone_number", phone).eq("status", "active").order("updated_at", { ascending: false }).limit(1).maybeSingle();
  if (!conversation) {
    const created = await db.from("conversations").insert({ phone_number: phone, current_step: "inquiry" }).select("*").single();
    if (created.error) return Response.json({ error: created.error.message }, { status: 500 });
    conversation = created.data;
  }

  await db.from("conversation_messages").insert({ conversation_id: conversation.id, sender_type: "user", message: text, metadata: { classification } });

  if (classification === "G") return Response.json({ reply: "Hello! I'm Jeff. Tell me what kind of accommodation you're looking for." });
  if (classification === "H") return Response.json({ reply: "I can help you find accommodation, compare options, start a booking and guide you through payment." });
  if (classification === "J") return Response.json({ reply: "I'm Jeff, an accommodation assistant. I help you find suitable properties and manage the booking process." });
  if (classification === "X") {
    await db.from("conversations").update({ current_step: "inquiry", context_data: {}, selected_properties: [], updated_at: new Date().toISOString() }).eq("id", conversation.id);
    return Response.json({ reply: "I've reset our conversation. You can start fresh." });
  }
  if (classification === "P") return Response.json({ reply: "Payment is handled after the provider accepts your booking. If you already have a payment reference, send it here." });
  if (classification === "N" || classification === "S") return Response.json({ reply: "Got it. Please continue with the current booking step." });

  const requirements = extractRequirements(text);
  const { data: results, error } = await db.rpc("search_properties", { p_heads: requirements.heads, p_budget_max: requirements.budget_max, p_rental_period: requirements.rental_period, p_amenities: [], p_gender_preference: requirements.gender_preference, p_distance_preference: requirements.distance_preference, p_location_context: null, p_limit: 5 });
  if (error) return Response.json({ error: error.message }, { status: 500 });
  await db.from("conversations").update({ current_step: "property_listings", context_data: { requirements, search_results: results ?? [] }, selected_properties: [], last_message_at: new Date().toISOString(), updated_at: new Date().toISOString() }).eq("id", conversation.id);
  const reply = results?.length ? results.map((p: any, i: number) => `${i + 1}. ${p.name} — ${p.price_per_month ?? "Price on request"} (match ${p.match_score})`).join("\n") : "I couldn't find a suitable property yet. Try changing your budget, room size or location.";
  return Response.json({ reply, classification, results: results ?? [] });
});
