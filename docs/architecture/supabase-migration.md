# Jeff: Django → Next.js + Supabase Migration

## Target architecture

The target application architecture is **Next.js on Vercel with Supabase as the backend platform**. The Django backend is treated as legacy functionality to migrate, not as the target application server.

```text
Next.js (Vercel)
      |
      +--> Supabase Auth
      +--> Supabase PostgreSQL
      +--> Supabase Storage
      +--> Supabase Realtime
      +--> Supabase Edge Functions (where server-side execution is required)
```

## Migration principles

1. Inventory existing Django functionality before removing it.
2. Recreate functionality in the smallest appropriate Next.js/Supabase primitive.
3. Put database structure and security policies under version control with Supabase migrations.
4. Use PostgreSQL Row Level Security (RLS) instead of relying on Django authorization for data access.
5. Keep Django operational only for functionality that has not yet been migrated.
6. Migrate and verify data before retiring Django components.
7. Remove Django only after its replacement is tested and production usage has been verified.

## Function mapping

| Django responsibility | Target implementation |
|---|---|
| Django models / ORM | Supabase PostgreSQL tables, views and functions |
| Django auth | Supabase Auth |
| Django API endpoints | Next.js Server Actions/Route Handlers or Supabase Edge Functions |
| Django authorization | PostgreSQL RLS + Supabase Auth claims |
| Django file handling | Supabase Storage |
| Django realtime behavior | Supabase Realtime |
| Background/server-only logic | Supabase Edge Functions or an appropriate scheduled/queue worker |
| Django migrations | `supabase/migrations/*.sql` |
| Frontend API client | `@supabase/supabase-js` / `@supabase/ssr` |

## Existing Django migration inventory

The current repository contains functionality around workflows, recommendations, providers, MCP integrations, matching, and WhatsApp. Each area must be mapped to a replacement before its Django implementation is removed.

## CI/CD direction

- Pull requests and pushes to `main` run validation.
- Vercel remains responsible for deployment through its Git integration.
- Supabase schema changes are reviewed as SQL migrations.
- CI validates the new Next.js/Supabase architecture while Django tests remain during the transition period.

## Initial migration phases

### Phase 1 — Inventory

Document Django models, endpoints, services, integrations, background tasks and tests.

### Phase 2 — Supabase foundation

Create Supabase project configuration, migrations, schema, RLS policies, Auth integration and required storage/realtime configuration.

### Phase 3 — Feature migration

Move one capability at a time from Django to Next.js/Supabase, retaining regression coverage.

### Phase 4 — Data migration

Move required production data into the new PostgreSQL schema and verify it.

### Phase 5 — Cutover

Switch Next.js to the Supabase implementation and monitor production behavior.

### Phase 6 — Django retirement

Remove obsolete Django services, dependencies, deployment configuration and tests after the migration is verified.
