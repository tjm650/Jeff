# Django functionality inventory

This is the starting inventory for migrating Jeff from Django to Next.js + Supabase. It is intentionally a map, not a direct schema conversion.

## Data/domain models identified

The Django `core` app currently contains models for:

- `AccommodationProvider`
- `Property`
- `Token`
- `Transaction`
- `Booking`
- `ConversationState`
- `Review`
- `APIKey`
- `Conversation`

The existing models contain relationships, status/state machines, JSON context fields, payment records, property availability, reviews, and conversation/security tracking. These should become purpose-designed PostgreSQL tables with explicit foreign keys, constraints, indexes and RLS rather than a mechanical Django-to-SQL translation.

## Initial target mapping

| Existing area | Supabase/Next.js target | Migration state |
|---|---|---|
| Accommodation providers | PostgreSQL + RLS | Not started |
| Properties/listings | PostgreSQL + RLS | Not started |
| Tokens/payment access | PostgreSQL + server-side functions/Edge Functions | Not started |
| Transactions | PostgreSQL + payment provider integration | Not started |
| Bookings | PostgreSQL + transactional server-side logic | Not started |
| Conversation state | PostgreSQL and/or Realtime | Not started |
| Reviews/ratings | PostgreSQL + SQL functions/triggers where appropriate | Not started |
| API keys | Supabase/Next.js server-side secrets and/or scoped credentials | Not started |
| Conversation/security tracking | PostgreSQL + RLS/audit strategy | Not started |
| WhatsApp integration | Edge Function or dedicated server-side integration | Not started |
| Provider integrations | Edge Functions/server-side Next.js modules | Not started |
| MCP integration | Server-side Next.js/Edge Function integration as supported | Not started |
| Matching/recommendation logic | TypeScript server-side logic + PostgreSQL queries/functions | Not started |
| Django authentication | Supabase Auth | Not started |

## Migration rules

- Do not delete Django models yet.
- Do not create the Supabase schema solely by copying Django models.
- For each model/service, identify its user-facing behavior, authorization rules, data dependencies, and tests first.
- Add Supabase migrations only when the target data model is understood.
- Add RLS policies as part of the same feature migration as the table.
- Keep regression tests around during the transition.

## Immediate next investigation

1. Enumerate Django URLs/views and their consumers.
2. Enumerate service modules and external integrations.
3. Inspect frontend API/data access and identify current Django dependencies.
4. Identify which existing SQLite data is valuable and must be migrated.
5. Design the first Supabase schema around the actual product flows.
