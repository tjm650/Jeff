import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";

const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
const verifyToken = Deno.env.get("WHATSAPP_VERIFY_TOKEN");

Deno.serve(async (req) => {
  if (req.method === "GET") {
    const url = new URL(req.url);
    if (url.searchParams.get("hub.mode") === "subscribe" && url.searchParams.get("hub.verify_token") === verifyToken) {
      return new Response(url.searchParams.get("hub.challenge") ?? "", { status: 200 });
    }
    return new Response("Forbidden", { status: 403 });
  }
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405 });
  const body = await req.json().catch(() => null);
  if (!body) return new Response("Bad request", { status: 400 });
  const value = body?.entry?.[0]?.changes?.[0]?.value;
  const message = value?.messages?.[0];
  if (message?.from) {
    const { data: conversation } = await supabase.from("conversations").select("id").eq("phone_number", message.from).eq("status", "active").order("updated_at", { ascending: false }).limit(1).maybeSingle();
    if (conversation) {
      await supabase.from("conversation_messages").insert({ conversation_id: conversation.id, sender_type: "user", message: message.text?.body ?? null, metadata: { whatsapp_message_id: message.id ?? null, type: message.type ?? null } });
      await supabase.from("conversations").update({ last_message_at: new Date().toISOString(), updated_at: new Date().toISOString() }).eq("id", conversation.id);
    }
  }
  return Response.json({ received: true });
});
