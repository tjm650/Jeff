# WhatsApp Diagnostics

Jeff now records a durable event trail for the WhatsApp pipeline.

## Dashboard

Open:

`/webhook/whatsapp/diagnostics/`

The dashboard requires a Jeff API key using either `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`.

For JSON:

`/webhook/whatsapp/diagnostics/?format=json`

Filters:

- `?correlation_id=<wamid-or-correlation-id>`
- `?phone_last4=2726`
- Combine filters as needed.

## What the dashboard tells you

A flow is grouped by correlation ID. Typical stages are:

1. `webhook_received` — Meta reached Jeff.
2. `message_extracted` — Jeff parsed an inbound message.
3. `business_processing` — Jeff entered the conversation/payment workflow.
4. `outbound_validate` — Jeff attempted an outbound WhatsApp send.
5. `meta_api_accepted` — Meta accepted the outbound request and returned a WhatsApp message ID.
6. `meta_delivery` — Meta later reported `sent`, `delivered`, `read`, or `failed`.
7. `webhook_response` — Jeff returned a response to Meta.

`FAILED` means an explicit error was recorded. `STUCK` means the most recent stage is still `started` for at least 10 seconds.

## Privacy

The diagnostic table stores only the last four digits of phone numbers. It does not store WhatsApp message bodies.

## Retention

The dashboard reads the most recent 24 hours. The database table is intentionally durable so events survive Render process restarts.

A later cleanup job should delete events older than the desired retention period (for example, 7 or 30 days).
