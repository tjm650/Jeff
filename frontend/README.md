# Jeff Frontend - Student Accommodation Platform

This is the frontend application for Jeff, an AI-powered student accommodation platform that helps students at NUST find suitable accommodation near campus.

## Overview

The Jeff frontend is built with Next.js 16.0.1 and provides:
- Landing page with project information
- Cart functionality for token purchases
- Privacy policy documentation

## Tech Stack

- **Framework**: Next.js 16.0.1 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Animation**: Motion library for smooth UI interactions
- **Icons**: FontAwesome for iconography
- **Content Security**: DOMPurify and sanitize-html for safe content rendering

## Project Structure

```
frontend/
├── app/                    # App router directory
│   ├── pages/              # Page components
│   │   ├── home/           # Home page
│   │    └── HomePage.tsx
├── components/              # Reusable UI components
│   ├── footer/              # Footer component
│    └── navigation/           # Navigation components
├── controller/              # API route handlers
│   ├── cartController/     # Cart functionality
├── public/                  # Static assets
│   ├── header-image.png
│   ├── jeff-header-msg-r.png
│   ├── jeff-header-msg-s.png
│    └── jeff-confirm-msg.png
└── package.json            # Dependencies and scripts
```

## Getting Started

First, install dependencies:

```bash
npm install
```

Then, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Pages

### Home Page (`/`)
- Landing page with project introduction
- WhatsApp integration call-to-action
- Privacy policy information

### Cart Page (`/cart`)
- Token purchase functionality
- Payment integration

### Privacy Page (`/privacy`)
- Privacy policy and terms of service

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run export` - Export static site
- `npm run lint` - Run ESLint

## Features

- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Smooth Animations**: Motion library for enhanced user experience
- **Type Safety**: Full TypeScript implementation
- **Modern UI**: Clean, professional interface

## Backend Integration

The frontend communicates with the Jeff backend API for:
- Token purchases and payment processing
- Property search functionality
- User authentication and session management

## Deployment

The frontend is configured for deployment on Vercel. The project includes:

- Next.js configuration (`next.config.ts`)
- TypeScript configuration (`tsconfig.json`)
- ESLint configuration (`eslint.config.mjs`)

## Environment Variables

Create a `.env.local` file for local development:

```env
NEXT_PUBLIC_FRONTEND_URL=http://localhost:3000
JEFF_WA_NUMBER=+263XXXXXXXXX
```

## Contributing

This frontend is part of the larger Jeff platform. For development guidelines, refer to the main project README.
