# Developer Interaction Blueprint

Technical implementation guide for the Jeff platform backend architecture and workflows.

## Architecture Overview

```
WhatsApp (Twilio/Meta)
    ↓
backend/whatsapp/whatsapp_handler.py
    ↓
core/services/conversation_workflow.py
    ↓
    ├─ matching/* (NLP, matcher, re-ranker)
    ├─ payment/* (paynow handler, tokens)
    ├─ providers/* (provider flows)
    └─ core/analytics.py
    ↓
Django Models (PostgreSQL/SQLite)
    ↓
Optional: Next.js Frontend (API consumers)
```

---

## Core Components

### 1. Conversation Engine

**Location**: `backend/core/services/conversation_workflow.py`

**Purpose**: Main orchestrator for all conversation flows

**Key Methods**:
- `process_message(cell_number, message, media_url)` - Main entry point
- Routes messages based on classification and current step
- Integrates recovery flow, welcome flow, and fail-safe handlers

**State Management**:
- Uses `ConversationState` model for state persistence
- Stores context in `context_data` JSON field
- Tracks current step, last action, timestamps

**Dependencies**:
- Message classifier
- Step handlers
- Property search
- Payment integration
- Help utils
- Recovery handler
- Fail-safe handler

---

### 2. Listing Fetcher

**Location**: `backend/matching/property_matcher.py`

**Purpose**: Property search and matching algorithm

**Key Methods**:
- `match_properties(requirements, limit)` - Main search method
- `_calculate_property_score(property, requirements)` - Scoring algorithm
- `_build_property_query(requirements)` - Database query builder

**Scoring Weights**:
- `heads_match`: 10.0 (most important)
- `budget_fit`: 8.0
- `distance_score`: 7.0
- `amenity_match`: 5.0
- `availability`: 5.0
- `rating_score`: 3.0
- `gender_preference`: 2.0

**Caching**: Results cached for 5 minutes using Redis (if available)

**API**: Internal function call (no REST endpoint currently)

---

### 3. Token System

**Location**: `backend/payment/handlers/token.py`

**Purpose**: Token management and validation

**Key Methods**:
- `get_valid_token(student_phone)` - Get active token
- `validate_token_usage(token)` - Check if token can be used
- `consume_for_full_view(token)` - Consume token for full property view
- `should_consume_for_preview()` - Returns False (previews are free)

**Token Lifecycle**:
1. Created after successful payment
2. Validated before property search
3. Consumed on "VIEW {number}" command
4. Refunded if booking rejected

**Storage**: `core/models.py::Token` model

---

### 4. Landlord Confirmation System

**Location**: `backend/providers/services/handlers.py`

**Purpose**: Handle provider responses to booking requests

**Flow**:
1. Booking created → Notification sent to provider
2. Provider responds via WhatsApp (YES/NO/Info request)
3. System processes response
4. Student notified of decision
5. Token refunded if rejected

**Key Methods**:
- `handle_provider_response(provider_phone, message)` - Process provider response
- `_process_provider_confirmation(booking, message)` - Handle acceptance
- `_process_provider_rejection(booking, message)` - Handle rejection
- `_refund_student_token(cell_number)` - Refund token on rejection

---

### 5. Session Memory

**Model**: `backend/core/models.py::ConversationState`

**Storage**: `context_data` JSON field

**Structure**:
```python
{
    'location': str,  # Last searched location
    'budget_max': float,  # Last budget preference
    'last_property_ids': [str],  # Recently viewed property UUIDs
    'cached_filters': dict,  # Search filters
    'user_preferences': dict,  # User preferences
    'last_action': str,  # Last action taken
    'last_action_timestamp': str,  # ISO timestamp
    'requirements': dict,  # Current search requirements
    'search_results': list,  # Current search results
    'search_metadata': dict,  # Search metadata
    'selected_property': dict,  # Currently selected property
    'selected_property_index': int,  # Index of selected property
    'current_property_page': int,  # Pagination page
    'total_matches': int  # Total matching properties
}
```

**Usage**:
- Recovery flow restoration
- Context-aware responses
- Preference memory across sessions

---

## Fail-Safe Rules Implementation

### Wrapper Pattern

All critical operations are wrapped with fail-safe handlers:

```python
response = fail_safe_handler.wrap_operation(
    operation_function,
    'context_name',
    *args, **kwargs
)
```

### Error Handling

**Null Response Handling**:
- Property search returns empty → Show "No properties found" message
- Payment verification pending → Show "Still checking..." message
- Provider timeout → Show follow-up options

**Random Text Detection**:
- Invalid input detected → Show help menu
- Valid commands bypass detection

**Payment Delays**:
- Payment pending > 30 seconds → Show "Still checking..." message
- Auto-retry mechanism for webhook verification

**Provider Timeouts**:
- No response after 24 hours → Show follow-up options
- Auto-reminder to provider (future enhancement)

---

## Scalability Considerations

### Database Optimization
- Indexed fields: `cell_number`, `current_step`, `is_active`
- JSON field queries optimized for `context_data`
- Property queries use `select_related()` and `prefetch_related()`

### Caching Strategy
- Property search results cached for 5 minutes
- Token validation cached (short TTL)
- Rate limiting uses Redis (if available)

### Async Tasks (Future)
- Celery integration for:
  - Payment webhook processing
  - Provider notifications
  - Token expiration cleanup
  - Analytics aggregation

---

## API Integration Points

### Twilio WhatsApp API
- **Sending**: `whatsapp_service.send_text_message(to_number, message)`
- **Templates**: `whatsapp_service.send_template_message(to_number, content_sid, variables)`
- **Receiving**: Webhook endpoint processes incoming messages

### Paynow Gateway
- **Initiation**: `paynow_service.create_agent_payment(whatsapp_number, payment_number)`
- **Webhook**: `payment/views.py::paynow_webhook()` processes status updates
- **Verification**: Idempotent webhook processing with signature verification (future)

### AI Services (MCP)
- **Classification**: `mcp_integration.classify_message(message)`
- **Extraction**: `mcp_integration.extract_requirements(message)`
- **Fallback**: Rule-based methods when AI unavailable

---

## Development Practices

### Local Development
- SQLite database for quick setup
- PostgreSQL-compatible types for production readiness
- Environment variables for all secrets

### Testing
- Unit tests for individual handlers
- Integration tests for complete workflows
- End-to-end tests for 8-step conversation flow

### Deployment
- Docker containerization (future)
- Environment-based configuration
- Gunicorn as WSGI server
- WhiteNoise for static files

### Monitoring
- Logging at all critical points
- Error tracking (Sentry integration recommended)
- Analytics hooks for metrics collection

---

## Module Dependencies

```
conversation_workflow.py
    ├─ message_classifier
    ├─ step_handlers
    │   ├─ property_search
    │   ├─ payment_integration
    │   ├─ help_utils
    │   └─ nlp_processor
    ├─ recovery_handler
    └─ fail_safe_handler

step_handlers.py
    ├─ property_search_handler
    ├─ payment_integration_handler
    ├─ help_utils_handler
    ├─ nlp_processor_handler
    ├─ welcome_handler
    ├─ location_flow_handler
    └─ ux_formatter

property_search.py
    ├─ property_matcher
    └─ ux_formatter

payment_integration.py
    ├─ payment_handler
    ├─ token_handler
    └─ ux_formatter
```

---

## Security Implementation

### Rate Limiting
- **Implementation**: `backend/core/views.py::_is_rate_limited()`
- **Limit**: 10 requests per 5-minute window per phone number
- **Storage**: Redis cache (if available) or in-memory

### Region Restriction
- **Implementation**: `whatsapp_service.validate_zimbabwe_number()`
- **Check**: Phone number must start with +263
- **Status**: Currently commented out for testing

### Input Validation
- All user inputs validated before processing
- Message classification prevents injection
- SQL injection prevented by Django ORM

### Conversation Tracking
- **Model**: `Conversation` model tracks all conversations
- **Purpose**: Security monitoring for suspicious activities
- **Fields**: `message_count`, `is_suspicious`, `flagged_reason`

---

## Future Enhancements

### Phase 1 (Current)
- ✅ Welcome flow
- ✅ Location flow
- ✅ Property previews
- ✅ Recovery flow
- ✅ UX formatter
- ✅ Fail-safe handlers

### Phase 2 (Planned)
- Token plans (multiple packages)
- Provider metrics tracking
- AI re-ranker for properties
- OpenStreetMap distance calculation
- Refund automation workflow

### Phase 3 (Future)
- Next.js admin dashboard
- Public listing website
- Multi-campus expansion
- Advanced analytics
- Celery async tasks

---

## Troubleshooting Guide

### Common Issues

**Issue**: Messages not being processed
- Check: Twilio webhook URL configuration
- Check: Rate limiting not blocking legitimate users
- Check: Database connection

**Issue**: Token not consumed
- Check: Token validation logic
- Check: Token expiration dates
- Check: Token usage count limits

**Issue**: Property search returns no results
- Check: Property `is_active` flag
- Check: Search criteria matching
- Check: Database query execution

**Issue**: Payment webhook not processing
- Check: Paynow webhook URL configuration
- Check: Webhook signature verification (if implemented)
- Check: Payment record lookup logic

---

## Code Organization

### Services Layer
- `core/services/conversation/` - Conversation handlers
- `core/services/booking/` - Booking workflow
- `core/services/mcp/` - AI integration

### Handlers Layer
- `payment/handlers/` - Payment processing
- `providers/services/` - Provider workflows
- `matching/` - Property matching algorithms

### Utils Layer
- `whatsapp/utils/` - WhatsApp service wrapper
- `payment/utils/` - Payment utilities
- `core/services/conversation/` - UX utilities

---

## Best Practices

1. **Always use UX formatter** for message formatting
2. **Wrap operations** with fail-safe handlers
3. **Store context** after each interaction
4. **Log all errors** with context
5. **Validate inputs** before processing
6. **Use feature flags** for new features
7. **Test edge cases** (null responses, timeouts, etc.)
8. **Document state transitions** clearly

---

## Contact & Support

For technical questions or issues:
- Check logs: `backend/logs/django.log`
- Review error messages in fail-safe handlers
- Check conversation state in Django admin
- Verify API configurations (Twilio, Paynow, AI keys)

