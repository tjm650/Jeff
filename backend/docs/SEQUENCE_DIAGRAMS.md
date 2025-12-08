# Sequence Diagrams

This document outlines key flow sequences for the Jeff platform conversation workflows.

## 1. Search Flow Sequence

```
User                    WhatsApp              Backend                    Database
 |                          |                     |                          |
 |--"Riverside"----------->|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--get_conversation_state->|
 |                          |                     |<--conversation----------|
 |                          |                     |--detect_location-------->|
 |                          |                     |--store_location--------->|
 |                          |                     |                          |--save
 |                          |<--"What's budget?"--|                          |
 |<--"What's budget?"-------|                     |                          |
 |                          |                     |                          |
 |--"$40-$60"------------->|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--parse_budget---------->|
 |                          |                     |--store_budget----------->|
 |                          |                     |                          |--save
 |                          |                     |--extract_requirements-->|
 |                          |                     |--match_properties------->|
 |                          |                     |                          |--query
 |                          |                     |<--properties-----------|
 |                          |                     |--format_previews--------|
 |<--"3 previews"-----------|                     |                          |
 |                          |                     |                          |
 |--"VIEW 1"--------------->|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--check_token----------->|
 |                          |                     |                          |--query
 |                          |                     |--consume_token--------->|
 |                          |                     |                          |--update
 |                          |                     |--format_full_details-->|
 |<--"Full details"---------|                     |                          |
 |                          |                     |                          |
 |--"Yes, contact"--------->|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--ask_for_name--------->|
 |<--"What's your name?"----|                     |                          |
```

---

## 2. Token Purchase Sequence

```
User                    WhatsApp              Backend              Paynow Gateway
 |                          |                     |                      |
 |--"USD PAY 0771234567"--->|                     |                      |
 |                          |--webhook---------->|                      |
 |                          |                     |--create_payment----->|
 |                          |                     |                      |--create
 |                          |                     |<--payment_url--------|
 |                          |                     |--update_conversation>|
 |<--"Payment initiated"----|                     |                      |
 |                          |                     |                      |
 |--[Approve on phone]------|                     |                      |
 |                          |                     |                      |
 |                          |<--webhook-----------|                      |
 |                          |--payment_status--->|                      |
 |                          |                     |--verify_payment----->|
 |                          |                     |--create_token--------|
 |                          |                     |--update_conversation>|
 |<--"Token created"--------|                     |                      |
```

---

## 3. Booking Flow Sequence

```
Student              WhatsApp          Backend              Provider          Database
 |                      |                 |                    |                  |
 |--"option-1"--------->|                 |                    |                  |
 |                      |--webhook------->|                    |                  |
 |                      |                 |--process_selection>|                  |
 |<--"What's name?"-----|                 |                    |                  |
 |                      |                 |                    |                  |
 |--"name-John Doe"---->|                 |                    |                  |
 |                      |--webhook------->|                    |                  |
 |                      |                 |--create_booking--->|                  |
 |                      |                 |                    |                  |--save
 |                      |                 |--send_to_provider-->|                  |
 |                      |                 |                    |--[WhatsApp]------|
 |<--"Request sent"-----|                 |                    |                  |
 |                      |                 |                    |                  |
 |                      |                 |                    |--"YES"--------->|
 |                      |<--webhook-------|                    |                  |
 |                      |--provider_msg-->|                    |                  |
 |                      |                 |--process_response->|                  |
 |                      |                 |--update_booking--->|                  |
 |                      |                 |                    |                  |--update
 |                      |                 |--notify_student--->|                  |
 |<--"Confirmed!"-------|                 |                    |                  |
```

---

## 4. Recovery Flow Sequence

```
User                    WhatsApp              Backend                    Database
 |                          |                     |                          |
 |[2+ hours inactivity]     |                     |                          |
 |                          |                     |                          |
 |--"Hi"------------------->|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--check_recovery--------->|
 |                          |                     |--get_conversation_state->|
 |                          |                     |                          |--query
 |                          |                     |<--conversation----------|
 |                          |                     |--check_inactivity------->|
 |                          |                     |--format_recovery--------|
 |<--"Welcome back!..."-----|                     |                          |
 |                          |                     |                          |
 |--"Yes"------------------>|                     |                          |
 |                          |--webhook---------->|                          |
 |                          |                     |--restore_context--------|
 |                          |                     |--continue_search-------->|
 |<--"Continuing search"----|                     |                          |
```

---

## 5. Property Preview → Full View Sequence

```
User                    Backend                    Database
 |                          |                          |
 |--[Search completes]----->|                          |
 |                          |--match_properties------->|
 |                          |<--properties-------------|
 |                          |--format_preview_mode---->|
 |<--"3 previews (free)"----|                          |
 |                          |                          |
 |--"VIEW 1"--------------->|                          |
 |                          |--check_token------------>|
 |                          |                          |--query
 |                          |--consume_token--------->|
 |                          |                          |--update
 |                          |--format_full_details---->|
 |<--"Full details"---------|                          |
 |                          |--store_viewed_property-->|
 |                          |                          |--save
```

---

## 6. Payment Webhook Sequence

```
Paynow Gateway         Backend                    Database
 |                         |                          |
 |--payment_status-------->|                          |
 |                         |--find_payment---------->|
 |                         |                          |--query
 |                         |<--payment---------------|
 |                         |--verify_status---------->|
 |                         |--update_payment-------->|
 |                         |                          |--update
 |                         |--create_token----------->|
 |                         |                          |--create
 |                         |--notify_user----------->|
 |                         |--[WhatsApp]-------------|
```

---

## State Transition Diagram

```
┌─────────┐
│ inquiry │
└────┬────┘
     │ (no token)
     ▼
┌─────────────┐
│ token_check │
└────┬────────┘
     │ (payment)
     ▼
┌──────────────────────┐
│ payment_confirmation │
└────┬─────────────────┘
     │ (token created)
     ▼
┌──────────────────┐
│ property_listings│ (preview mode)
└────┬─────────────┘
     │ (VIEW {number})
     ▼
┌──────────────────┐
│ property_listings│ (full view, token consumed)
└────┬─────────────┘
     │ (Contact landlord)
     ▼
┌─────────────────┐
│ name_collection │
└────┬────────────┘
     │ (name provided)
     ▼
┌─────────────────┐
│ booking_request │
└────┬────────────┘
     │ (provider responds)
     ▼
┌──────────────────┐
│provider_response │
└────┬─────────────┘
     │ (if accepted)
     ▼
┌──────────────────────┐
│booking_confirmation │
└─────────────────────┘
```

---

## Error Handling Flow

```
User                    Backend                    Fail-Safe Handler
 |                          |                              |
 |--[Invalid input]-------->|                              |
 |                          |--process_message------------>|
 |                          |--handle_random_text--------->|
 |                          |                              |--detect_invalid
 |                          |<--help_message--------------|
 |<--"Help menu"------------|                              |
 |                          |                              |
 |--[API error]------------>|                              |
 |                          |--wrap_operation------------->|
 |                          |                              |--catch_exception
 |                          |<--error_message-------------|
 |<--"Friendly error"-------|                              |
```

---

## Notes

- All sequences show the main happy path
- Error handling and fail-safe mechanisms are integrated at each step
- Token consumption only happens on "VIEW {number}" command
- Previews are free and don't consume tokens
- Recovery flow activates after 2+ hours of inactivity
- All state is persisted in `ConversationState.context_data`

