# Supabase project

This directory contains the version-controlled Supabase configuration and database migrations for Jeff.

## Migration policy

- All schema changes must be represented by SQL files under `supabase/migrations/`.
- Do not make untracked production schema changes that are not subsequently captured in a migration.
- RLS policies belong in migrations alongside the tables they protect.
- The Supabase database is the target backend for the Next.js application.

## Planned structure

```text
supabase/
├── README.md
├── config.toml
└── migrations/
```

The initial schema will be added after the existing Django models and application behavior have been inventoried. This avoids prematurely copying Django's schema into the target architecture.
