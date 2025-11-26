# Jeff - Student Accommodation Platform

Jeff is an AI-powered student accommodation platform that helps students at NUST (National University of Science and Technology) find suitable accommodation near campus through WhatsApp conversations.

## Project Overview

Jeff provides a conversational AI agent that operates via WhatsApp to help students:
- Find accommodation based on their specific requirements
- Process payments for property search tokens
- Facilitate booking requests and provider responses
- Provide personalized recommendations using NLP and AI

## Architecture

The project follows a full-stack microservices architecture:

### Backend (`/backend`)
- **Framework**: Django 5.1.1 with Django REST Framework
- **Database**: SQLite3 (development), PostgreSQL (production-ready)
- **Real-time Communication**: Channels and WebSockets
- **Payment Integration**: Paynow gateway for mobile money payments
- **AI Services**: Integration with OpenAI, Google Gemini, and Anthropic for NLP processing
- **WhatsApp Integration**: Twilio for WhatsApp messaging

### Frontend (`/frontend`)
- **Framework**: Next.js 16.0.1 with TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Motion library for smooth UI interactions

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL (for production)

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
   # Edit .env with your configuration
   python manage.py migrate
   python manage.py runserver
   ```

3. **Set up the frontend**
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## Project Structure

```
Jeff/
├── backend/                 # Django backend API server
│   ├── README.md            # Backend-specific documentation
│   ├── core/                # Main application logic
│   ├── payment/             # Payment processing system
│   ├── matching/            # Property matching algorithms
│   ├── providers/           # Provider management
│   └── whatsapp/            # WhatsApp integration
├── frontend/                # Next.js frontend application
│   ├── README.md            # Frontend-specific documentation
│   ├── app/                 # App router pages
│   ├── components/         # Reusable UI components
│   └── public/              # Static assets
├── privacy/                 # Documentation and privacy policies
├── Makefile                 # Development commands
├── render.yaml              # Production deployment configuration
└── README.md                # This file
```

## Key Features

### Core Functionality
- **8-Step Conversation Workflow**: Guided accommodation search process
- **Token-based Access**: Students purchase tokens for property search capabilities
- **NLP Processing**: Advanced natural language processing for requirement extraction
- **Property Matching**: AI-enhanced property recommendation system
- **Payment Processing**: Secure mobile money payments via Paynow
- **Provider Management**: Separate workflow for accommodation providers
- **Analytics Dashboard**: Comprehensive metrics and insights

### Security & Validation
- **Rate Limiting**: Prevents spam and abuse
- **Region Restriction**: Only available for Zimbabwe phone numbers
- **Input Validation**: Comprehensive validation for all user inputs
- **Conversation Tracking**: Security monitoring for suspicious activities

## Development Commands

The project includes a Makefile with common development commands:

```bash
# Start frontend development server
make frontend

# Start backend with ngrok for webhook testing
make runserver

# Create superuser
make createsuperuser

# Generate API key for frontend
make GAK
```

## Documentation

- **[Backend Documentation](./backend/README.md)** - Detailed backend setup, API endpoints, and development guide
- **[Frontend Documentation](./frontend/README.md)** - Frontend development guide and project structure

## Deployment

### Backend (Render.com)
The backend is configured for deployment on Render.com. The `render.yaml` file contains the deployment configuration.

### Frontend (Vercel)
The frontend is configured for deployment on Vercel with Next.js.

## Environment Configuration

See individual README files for detailed environment variable setup:
- [Backend Environment Variables](./backend/README.md#environment-variables)
- [Frontend Environment Variables](./frontend/README.md#environment-variables)

## Testing

```bash
# Backend tests
cd backend
python manage.py test

# Frontend tests
cd frontend
npm test
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary software. All rights reserved.

## Contact

For questions or support, please contact the development team.