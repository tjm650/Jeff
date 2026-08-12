# Jeff Django functionality inventory

This inventory is the migration checklist for replacing Django with Next.js + Supabase. It is intentionally a capability inventory rather than a one-to-one schema conversion.

## Core data and business capabilities

| Capability | Existing Django implementation | Target | Migration status |
|---|---|---|---|
| Accommodation providers | `core.models.AccommodationProvider` | Supabase `providers` table + RLS | Planned |
| Properties/listings | `core.models.Property` | Supabase `properties` + indexes/views | Planned |
| Tokens / search access | `core.models.Token` | Supabase token/entitlement tables + server-side RPC/Edge Function | Planned |
| Payments/transactions | `core.models.Transaction`, payment package | Supabase transactions + Edge Function/payment provider integration | Planned |
| Bookings | `core.models.Booking` | Supabase bookings + RLS + transactional RPCs | Planned |
| Conversation state | `core.models.ConversationState` | Supabase conversation state tables + Realtime where useful | Planned |
| Reviews | `core.models.Review` | Supabase reviews + database aggregation | Planned |
| API keys | `core.models.APIKey` | Prefer Supabase Auth/service roles; secrets stay server-side | Planned |
| Conversation security/audit | `core.models.Conversation` | Supabase conversation/audit tables + RLS | Planned |

## HTTP/API capabilities

The Django core routes currently expose WhatsApp webhook handling, payment verification, health/status endpoints, analytics dashboards, analytics for conversations/properties/revenue, and documentation download. These are not all client-side responsibilities.

- WhatsApp webhook → Supabase Edge Function (or a dedicated server-side function) because it is an external webhook.
- Payment verification → Supabase Edge Function because credentials and verification logic must remain server-side.
- Health/status → Vercel/Supabase observability or a small server-side health endpoint.
- Analytics → SQL views/functions and protected admin queries, with server-side aggregation where needed.
- Documentation download → Supabase Storage or static Vercel asset, depending on access requirements.

## Conversation workflow

The Django conversation workflow currently implements inquiry, token checking, property listings, name collection, booking request, provider response, information request, booking confirmation, payment confirmation, cleanup, help, greeting, Jeff-about, restart, media handling and provider routing.

The target should model the workflow as explicit application state and database transitions rather than porting the Django class unchanged. The workflow currently depends on WhatsApp, property search, payment integration, NLP/message classification, help utilities and provider workflow modules.

## Migration order

1. Properties/providers and search data model.
2. Supabase Auth and user identity model.
3. Conversation persistence and RLS.
4. Booking lifecycle.
5. Token/entitlement and payment lifecycle.
6. Reviews and ratings.
7. Provider workflow.
8. WhatsApp webhook and conversation orchestration.
9. Analytics/admin reporting.
10. Remaining legacy utilities and documentation delivery.
11. Data migration and Django retirement.

## Security requirements

- Browser clients use only the Supabase anon/publishable key.
- Service-role credentials are never exposed to the browser.
- Every user-owned table receives RLS policies before client access is enabled.
- Provider/admin capabilities use explicit authorization claims/roles rather than trusted client fields.
- Payment and webhook secrets remain in Edge Functions/server-side environment variables.
