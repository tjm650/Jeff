# Jeff Backend - Django API Server

This is the backend API server for Jeff, an AI-powered student accommodation platform built with Django.

## Overview

The Jeff backend provides:
- WhatsApp webhook handling for conversational AI
- Payment processing via Paynow gateway
- Property matching and recommendation algorithms
- Conversation state management
- Analytics and reporting
- Provider management system

## Tech Stack

- **Framework**: Django 5.1.1 with Django REST Framework
- **Database**: SQLite3 (development), PostgreSQL (production-ready)
- **Real-time**: Channels and WebSockets
- **AI Integration**: OpenAI, Google Gemini, Anthropic
- **Payment**: Paynow mobile money integration
- **Messaging**: Twilio WhatsApp API
- **Caching**: Redis (production)
- **Static Files**: WhiteNoise for static file serving

## Project Structure

```
backend/
├── backend/                 # Django project settings
│   ├── settings.py          # Main configuration
│   ├── urls.py              # URL routing
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
├── core/                     # Main application
│   ├── models.py             # Database models
│   ├── views.py              # API views and webhooks
│   ├── services/             # Business logic services
│   │   ├── conversation_workflow.py    # Main conversation handler
│   │   ├── conversation/                # Modular conversation components
│   │   ├── booking_workflow.py          # Booking management
│   │   └── mcp.py                        # Model Context Protocol integration
│   ├── analytics.py          # Analytics and metrics
│   ├── authentication.py     # API key authentication
│   └── middleware.py         # Custom middleware
├── payment/                   # Payment processing
│   ├── payment_handler.py     # Main payment handler
│   ├── handlers/              # Modular payment components
│   │   ├── core.py           # Core payment logic
│   │   ├── token.py          # Token management
│   │   ├── gateway.py        # Payment gateway integration
│   │   ├── receipt.py        # Receipt generation
│   │   ├── cleanup.py        # Transaction cleanup
│   │   └── history.py        # Payment history
│   ├── utils/                 # Payment utilities
│   │   ├── payment_processor.py
│   │   └── paynow_service.py
│   └── models.py             # Payment models
├── matching/                  # Property matching algorithms
│   ├── property_matcher.py    # Property matching logic
│   ├── nlp_classifier.py      # NLP for requirement extraction
│   ├── rental_period_extractor.py
│   └── requirement_extractor.py
├── providers/                 # Provider management
│   ├── services/             # Provider workflow
│   └── insights/             # Provider analytics
├── whatsapp/                  # WhatsApp integration
│   ├── whatsapp_handler.py   # Webhook handler
│   └── utils/                 # WhatsApp utilities
├── manage.py                  # Django management script
├── requirements.txt          # Python dependencies
└── runtime.txt               # Python runtime version
```

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (for production)
- Redis (for production caching)

### Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Environment Variables

Create a `.env` file in the backend directory:

```env
# Django Settings
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*.onrender.com

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# API Keys
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
ANTHROPIC_API_KEY=your-anthropic-key

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_NUMBER=+1234567890

# Payment Configuration
PAYNOW_INTEGRATION_ID=your-integration-id
PAYNOW_INTEGRATION_KEY=your-integration-key
TOKEN_PRICE_USD=1.00
TOKEN_PRICE_ZWG=25.7

# Ngrok Configuration (optional)
NGROK_AUTH_TOKEN=your-ngrok-token
USE_NGROK=False
```

## API Endpoints

### Core Endpoints
- `POST /webhook/whatsapp/` - Main WhatsApp webhook
- `GET /health/` - Health check endpoint
- `GET /system-status/` - Comprehensive system status
- `GET /analytics/` - Analytics dashboard
- `GET /conversation-analytics/` - Conversation metrics
- `GET /property-analytics/` - Property performance data
- `GET /revenue-analytics/` - Revenue tracking

### Payment Endpoints
- `POST /payment/webhook/` - Payment gateway webhook
- `GET /payment/history/<phone>/` - Payment history

## Development

### Running Tests
```bash
python manage.py test

# Run specific test modules
python manage.py test core.tests.test_workflow
python manage.py test payment.tests
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset database
python manage.py flush
```

### Using Make Commands
```bash
make runserver      # Start with ngrok
make createsuperuser # Create admin user
make GAK            # Generate API key
```

## Key Features

### Conversation Workflow
The backend implements an 8-step conversation workflow:
1. Student Inquiry
2. Token Check
3. Property Listings
4. Name Collection
5. Booking Request
6. Provider Response
7. Info Request
8. Cleanup & Close

### Payment Processing
- Token-based access system
- Paynow mobile money integration
- Transaction tracking and validation
- Receipt generation

### AI Integration
- Natural language processing for requirement extraction
- Property matching algorithms
- Conversation state management
- Provider response handling

## Deployment

The backend is configured for deployment on Render.com. Key production settings:

- PostgreSQL database
- Redis for caching
- WhiteNoise for static files
- Gunicorn as WSGI server
- Environment-based configuration

## Monitoring & Analytics

The system provides comprehensive analytics:
- Conversation metrics
- Property performance
- Revenue tracking
- User engagement
- Provider insights

## Contributing

Refer to the main project README for contribution guidelines.