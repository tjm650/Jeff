# API Triggers & Developer Guide

This document outlines all conversation triggers, API endpoints, handlers, and state transitions in the Jeff platform.

## Overview

The Jeff platform uses a WhatsApp-first conversational interface with an 8-step workflow. All interactions are triggered via WhatsApp messages and processed through Django backend handlers.

## Core Endpoints

### 1. WhatsApp Webhook

**Endpoint**: `POST /webhook/whatsapp/`

**Handler**: `backend/core/views.py::whatsapp_webhook()`

**Purpose**: Main entry point for all WhatsApp messages

**Request Format**:
- `From`: WhatsApp phone number (e.g., `whatsapp:+263712345678`)
- `Body`: Message text
- `MediaUrl0`: Optional media URL

**Response**: JSON response (message sent via Twilio)

**Flow**:
1. Extract message data from Twilio webhook
2. Validate phone number and region (+263 for Zimbabwe)
3. Rate limiting check (10 requests per 5 minutes)
4. Create/update conversation tracking
5. Route to `conversation_workflow.process_message()`
6. Send response via WhatsApp

---

## Conversation Flow Triggers

### 1. Welcome Flow

**Trigger**: First message from new user OR greeting message

**Detection**:
- `welcome_handler.check_first_time_user()` - Checks if `last_message_at == created_at` (within 1 minute)
- `welcome_handler.should_show_welcome()` - Checks conversation state

**Handler**: `backend/core/services/conversation/welcome_handler.py`

**State**: `current_step = 'inquiry'`

**Response**: Welcome message with quick replies:
- 🔍 Search rooms
- 💰 Buy token
- 🎒 Student rooms near NUST
- 🏘 General Bulawayo rooms
- ❓ Help

**Quick Reply Routing**:
- `search` → Location flow
- `buy_token` → Payment flow (`token_check` step)
- `nust_rooms` → Set location to NUST, ask budget
- `general_rooms` → Continue with normal flow
- `help` → Show help menu

---

### 2. Search Flow

**Trigger**: User sends location OR selects "🔍 Search rooms"

**Handler**: `backend/core/services/conversation/step_handlers.py::_handle_inquiry_step()`

**State Transitions**:
- `inquiry` → `token_check` (if no token)
- `inquiry` → `property_listings` (if token valid)

**Location Detection**:
- `location_flow_handler.detect_location_from_message()` - Extracts Bulawayo locations
- Stores in `conversation.context_data['location']`

**Budget Selection**:
- `location_flow_handler.ask_budget_with_quick_replies()` - Shows budget options
- `location_flow_handler.parse_budget_quick_reply()` - Parses budget from quick reply
- Stores in `conversation.context_data['budget_max']`

**API Calls**:
- `GET /api/properties/search/?location=...&budget=...` (internal)
- `property_matcher.match_properties()` - Property matching algorithm

---

### 3. Token Purchase

**Trigger**: User sends "USD PAY {number}" OR "ZWG PAY {number}" OR selects "✔ Buy token"

**Handler**: `backend/core/services/conversation/payment_integration.py::handle_payment_request()`

**State**: `current_step = 'payment_confirmation'`

**API Calls**:
- `POST /api/payments/paynow/initiate/` (internal)
- Paynow gateway API for payment initiation

**Flow**:
1. Extract payment number and currency from message
2. Validate payment number format
3. Check for recent pending payments
4. Create Payment record
5. Initiate Paynow payment
6. Update conversation state with pending payment
7. Wait for payment confirmation

**Webhook**: `POST /api/payments/paynow/webhook/` - Receives payment status updates

---

### 4. Property View (Preview Mode)

**Trigger**: Property search completes (automatic)

**Handler**: `backend/core/services/conversation/property_search.py::_format_preview_mode()`

**State**: `current_step = 'property_listings'`

**Token Consumption**: None (previews are free)

**Response**: Shows 3 property previews with "VIEW {index}" CTAs

**Storage**: Properties stored in `conversation.context_data['search_results']`

---

### 5. Property View (Full Details)

**Trigger**: User sends "VIEW {number}"

**Handler**: `backend/core/services/conversation/step_handlers.py::_handle_property_listings_step()`

**State**: `current_step = 'property_listings'`

**Token Consumption**: Yes (token consumed on VIEW command)

**Flow**:
1. Validate token exists and is valid
2. Extract property index from "VIEW {number}"
3. Consume token (`token_handler.consume_for_full_view()`)
4. Store viewed property ID in `conversation.context_data['last_property_ids']`
5. Format and return full property details
6. Show "Contact Landlord" prompt with quick replies

---

### 6. Landlord Contact

**Trigger**: User selects "📞 Yes, contact landlord" after viewing full property details

**Handler**: `backend/core/services/conversation/step_handlers.py::_handle_property_listings_step()` → `_process_property_selection()`

**State Transitions**:
- `property_listings` → `name_collection` (asks for student name)
- `name_collection` → `booking_request` (creates booking)

**API Calls**:
- `POST /api/bookings/` (internal) - Creates booking record
- Twilio API - Sends booking notification to provider

**Flow**:
1. User selects property (option-{number} or after VIEW)
2. System asks for student name
3. User provides name (name-{full name})
4. System creates Booking record
5. System sends notification to provider via WhatsApp
6. Conversation moves to `booking_request` step
7. Waits for provider response

---

### 7. Provider Response

**Trigger**: Provider sends confirmation/rejection via WhatsApp

**Handler**: `backend/providers/services/handlers.py::handle_provider_response()`

**State Transitions**:
- `booking_request` → `provider_response` (provider responds)
- `provider_response` → `booking_confirmation` (if accepted)
- `provider_response` → `inquiry` (if rejected, token refunded)

**Provider Response Types**:
- `YES/CONFIRMED` → Booking confirmed
- `NO/REJECT` → Booking rejected, token refunded
- Info request → Ask for additional information

**Student Notification**: Sent via WhatsApp template message

---

### 8. Recovery Flow

**Trigger**: User returns after 2+ hours of inactivity

**Detection**: `recovery_handler.check_recovery_needed()` - Checks time since last message and stored context

**Handler**: `backend/core/services/conversation/recovery_handler.py`

**State**: `current_step = 'inquiry'` (typically)

**Response**: Recovery message with last location/budget context

**Quick Replies**:
- "Yes" → Continue with previous search
- "Show new listings" → Clear old results, keep location/budget
- "Start over" → Reset completely

---

## State Machine

```
inquiry
  ↓ (no token)
token_check
  ↓ (payment)
payment_confirmation
  ↓ (token created)
property_listings (preview mode)
  ↓ (VIEW {number})
property_listings (full view, token consumed)
  ↓ (Contact landlord)
name_collection
  ↓ (name provided)
booking_request
  ↓ (provider responds)
provider_response
  ↓ (if accepted)
booking_confirmation
  ↓ (if rejected)
inquiry (token refunded)
```

---

## Message Classification

**Handler**: `backend/core/services/conversation/message_classifier.py`

**Classifications**:
- `G` - Greeting
- `A` - Accommodation enquiry
- `H` - Help
- `P` - Payment
- `S` - Property selection (option-{number})
- `N` - Name collection (name-{name})
- `X` - Abort/Restart
- `J` - Jeff about

**Routing**: Based on classification, message is routed to appropriate handler

---

## API Endpoints (Internal)

### Property Search
- **Method**: Internal function call
- **Handler**: `matching/property_matcher.py::match_properties()`
- **Parameters**: Requirements dict (location, budget, amenities, etc.)
- **Returns**: List of matched properties with scores

### Token Management
- **Get Valid Token**: `payment/handlers/token.py::get_valid_token()`
- **Consume Token**: `payment/handlers/token.py::consume_for_full_view()`
- **Validate Token**: `payment/handlers/token.py::validate_token_usage()`

### Booking Creation
- **Method**: Internal function call
- **Handler**: `core/services/conversation/step_handlers.py::_create_booking()`
- **Creates**: Booking record, sends notification to provider

### Payment Processing
- **Initiate**: `payment/payment_handler.py::initiate_payment()`
- **Webhook**: `payment/views.py::paynow_webhook()`
- **Status Check**: `payment/handlers/gateway.py::check_payment_status()`

---

## Error Handling

All operations are wrapped with fail-safe handlers:

- **Null Responses**: `fail_safe_handler.handle_null_response(context)`
- **Payment Delays**: `fail_safe_handler.handle_payment_delay(payment)`
- **Provider Timeouts**: `fail_safe_handler.handle_provider_timeout(booking)`
- **Random Text**: `fail_safe_handler.handle_random_text(message)`

---

## Context Data Structure

See `backend/core/models.py::ConversationState` for documented `context_data` schema.

Key fields:
- `location`: Last searched location
- `budget_max`: Last budget preference
- `last_property_ids`: Recently viewed property UUIDs
- `search_results`: Current search results
- `selected_property`: Currently selected property
- `last_action`: Last action taken
- `last_action_timestamp`: ISO timestamp

---

## Integration Points

1. **Twilio WhatsApp API**: All message sending/receiving
2. **Paynow Gateway**: Payment processing
3. **AI Services** (MCP): NLP classification and requirement extraction
4. **Database**: All state persistence via Django ORM
5. **Redis** (optional): Caching and rate limiting

---

## Security & Validation

- **Rate Limiting**: 10 requests per 5-minute window per phone number
- **Region Restriction**: Only Zimbabwe phone numbers (+263)
- **Input Validation**: All user inputs validated before processing
- **Conversation Tracking**: Security monitoring via `Conversation` model

