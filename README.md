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
- **WhatsApp Integration**: WhatsApp/Meta and Twilio support
- **Matching**: Property search and recommendation workflow
- **Bookings**: Provider-facing booking and confirmation workflow

### Frontend (`/frontend`)
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Motion library

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL for production deployments

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Jeff
   ```

2. **Set up the backend**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   python manage.py migrate
   python manage.py runserver
   ```

3. **Set up the frontend**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

## Project Structure

```text
Jeff/
├── backend/                 # Django backend API server
│   ├── core/                # Conversation, search, booking and shared logic
│   ├── matching/            # Property matching algorithms
│   ├── providers/           # Provider management and booking workflow
│   └── whatsapp/            # WhatsApp integration
├── frontend/                # Next.js frontend application
├── supabase/                # Supabase functions and infrastructure
├── privacy/                 # Documentation and privacy policies
├── Makefile                 # Development commands
├── render.yaml              # Legacy backend deployment configuration
└── README.md                # Project documentation
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

## Development Commands

```bash
make frontend
make runserver
make createsuperuser
make GAK
```

## Deployment

The frontend is configured for Vercel/Next.js deployment. The existing Django backend can still run using the current deployment configuration while the broader Vercel/Supabase migration is completed.

## Testing

```bash
cd backend
python manage.py test

cd ../frontend
npm test
```

## Roadmap

1. Stabilize free accommodation search
2. Stabilize property selection and booking
3. Stabilize provider responses and confirmations
4. Complete the Vercel/Supabase backend migration
5. Add observability and end-to-end diagnostics
6. Design and implement payment architecture as a separate future phase

## License

This project is proprietary software. All rights reserved.

## Contact

For questions or support, please contact the development team.

<!-- Free-mode verification trigger -->
