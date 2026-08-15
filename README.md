# Jeff - Student Accommodation Platform

Jeff is an AI-powered student accommodation platform that helps students find suitable accommodation near campus through WhatsApp conversations.

## Current Free-Use Mode

Jeff is currently **free to use**. Payment processing and paid search tokens are disabled while the core accommodation workflow is being stabilized.

Users can:
- Find accommodation based on their requirements
- Receive property recommendations
- Select properties
- Submit booking requests
- Communicate with accommodation providers
- Receive booking confirmations

Payment architecture will be reintroduced later as a separate, deliberate feature once search and booking are fully stable.

## Architecture

### Backend (`/backend`)
- **Framework**: Django with Django REST Framework
- **Database**: SQLite for development, PostgreSQL for production
- **Real-time Communication**: Channels and WebSockets
- **AI Services**: OpenAI, Google Gemini, and Anthropic integrations for NLP processing
- **WhatsApp Integration**: Meta WhatsApp Cloud API
- **Matching**: Property search and recommendation workflow
- **Bookings**: Provider-facing booking and confirmation workflow

### Frontend (`/frontend`)
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Motion library

### WhatsApp transport

Meta WhatsApp Cloud API is the only supported production WhatsApp transport.

The public Meta webhook is owned by the Supabase Edge Function `whatsapp-webhook`.

The webhook:
1. verifies the Meta signature;
2. records every inbound/status event in Supabase;
3. deduplicates Meta retries by event key;
4. records inbound/outbound message state;
5. invokes the existing JEFF conversation engine;
6. records Meta outbound message IDs and delivery states.

The Django WhatsApp client remains available to domain workflows such as provider notifications, but it is Meta-only. It must not use Twilio credentials or Twilio Content SIDs.

### Required server-side environment

Meta/Supabase:
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_APP_SECRET`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_GRAPH_VERSION` (optional)
- `JEFF_CONVERSATION_FUNCTION_URL` (optional)

Django provider notifications:
- `META_ACCESS_TOKEN` or `WHATSAPP_ACCESS_TOKEN`
- `META_PHONE_NUMBER_ID` or `WHATSAPP_PHONE_NUMBER_ID`
- `META_API_VERSION`
- `META_TEMPLATE_LANGUAGE`
- `META_TEMPLATE_PROVIDER_INFO_RESPONSE`

Do not configure or commit Twilio credentials for JEFF WhatsApp.

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL for production deployments

### Development Setup

1. Clone the repository.
2. Set up the backend with the project's environment configuration.
3. Set up the frontend.
4. For WhatsApp development, use Meta's test assets and a dedicated test number.

## Project Structure

```text
Jeff/
├── backend/                 # Django backend API server
│   ├── core/                # Conversation, search, booking and shared logic
│   ├── matching/            # Property matching algorithms
│   ├── providers/           # Provider management and booking workflow
│   └── whatsapp/            # Meta WhatsApp client and compatibility webhook
├── frontend/                # Next.js frontend application
├── supabase/                # Supabase functions and infrastructure
├── privacy/                 # Documentation and privacy policies
└── README.md
```

## Key Features

### Core Functionality
- **Free accommodation search**: No payment or token purchase is required
- **Natural-language requirements**: Users can describe what they need conversationally
- **Property matching**: Search and recommendation based on budget, location, room configuration and amenities
- **Booking workflow**: Users can select a property and submit a booking request
- **Provider workflow**: Accommodation providers can respond to booking requests
- **Booking confirmation**: The workflow supports provider responses and final confirmation
- **Analytics**: Search and booking insights

### Security & Validation
- Rate limiting and abuse protection
- Zimbabwe phone-number validation where applicable
- Input validation
- WhatsApp webhook signature validation
- Conversation tracking and security monitoring
- Durable WhatsApp event/message tracing

## Deployment

The frontend is configured for Vercel/Next.js deployment. The Django backend can still run using the existing deployment configuration while the broader Vercel/Supabase migration is completed.

The Meta WhatsApp callback must point to the deployed Supabase `whatsapp-webhook` Edge Function, not the legacy Django webhook.

## Testing

```bash
cd backend
python manage.py test
```

For WhatsApp, test the real Meta webhook with a controlled phone number after deployment.

## Roadmap

1. Stabilize free accommodation search
2. Stabilize property selection and booking
3. Stabilize provider responses and confirmations
4. Complete the Vercel/Supabase backend migration
5. Complete WhatsApp observability and end-to-end diagnostics
6. Design and implement payment architecture as a separate future phase

## License

This project is proprietary software. All rights reserved.

## Contact

For questions or support, please contact the development team.
