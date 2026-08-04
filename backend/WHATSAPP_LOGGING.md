# WhatsApp Webhook Logging Configuration

This document describes how WhatsApp webhook logs are displayed when initiating or deploying the server.

## Overview

The system now provides comprehensive logging of WhatsApp webhook configuration and status at several key points:

1. **Server Startup** - When Django apps initialize
2. **WSGI Deployment** - When the application is deployed
3. **Webhook Verification** - When Meta verifies the webhook
4. **Deployment Status Check** - Dedicated deployment logging script

## Log Output Examples

### 1. App Initialization Logs

When the Django server starts, the WhatsApp app logs its configuration:

```
================================================================================
[START] WhatsApp Integration Module Initialized
================================================================================
WhatsApp Webhook Configuration Status:
   [OK] META_VERIFY_TOKEN: [OK] Configured
   [OK] META_APP_SECRET: [OK] Configured
   [OK] WEBHOOK_SECRET: [WARN] NOT configured

WhatsApp Webhook Endpoints:
   - GET:  https://jeff-backend-n5kb.onrender.com/webhook/whatsapp/
   - POST: https://jeff-backend-n5kb.onrender.com/webhook/whatsapp/

Security Configuration:
   [OK] DEBUG mode: OFF
   [OK] CSRF exemption: [OK] Enabled

[READY] WhatsApp module ready to receive webhook events
================================================================================
```

### 2. WSGI Deployment Logs

When the application is deployed via Gunicorn:

```
================================================================================
[DEPLOYED] WSGI Application Deployed
================================================================================
Environment: Render
DEBUG mode: false
WhatsApp webhooks are now active and ready to receive Meta Cloud API events
================================================================================
```

### 3. Webhook Verification Logs

When Meta Cloud API verifies the webhook endpoint:

```
============================================================
[VERIFY] WhatsApp Webhook Verification Request
============================================================
Mode: subscribe
Token verification: [PASS]
Challenge received: 1234567890abcdef...

[OK] WhatsApp webhook successfully connected and verified
============================================================
```

### 4. Deployment Status Check

Run the deployment status check script:

```bash
python log_whatsapp_webhook_status.py
```

Output includes:

```
==========================================================================================
[DEPLOY] JEFF PLATFORM - WHATSAPP WEBHOOK DEPLOYMENT STATUS
==========================================================================================

[ENVIRONMENT] DEPLOYMENT ENVIRONMENT:
   Environment: Render
   DEBUG Mode: OFF [OK]
   Python: 3.10.13
   Django: 5.1

[HOSTS] ALLOWED HOSTS:
   - jeff-backend-n5kb.onrender.com
   - *.onrender.com

[CONFIG] WHATSAPP WEBHOOK CONFIGURATION:
   [OK] META_VERIFY_TOKEN: Configured (length: 32)
   [OK] META_APP_SECRET: Configured (length: 40)
   [WARN] WEBHOOK_SECRET: NOT CONFIGURED

[ENDPOINTS] WEBHOOK ENDPOINTS:
   GET (Verification):  https://jeff-backend-n5kb.onrender.com/webhook/whatsapp/
   POST (Messages):     https://jeff-backend-n5kb.onrender.com/webhook/whatsapp/

[SECURITY] SECURITY CONFIGURATION:
   CSRF Exempt: [OK] Enabled for webhook endpoints
   Signature Verification: [OK] Enabled
   HTTPS Required: [OK] Yes (production)

[APPS] INSTALLED APPS STATUS:
   [OK] WhatsApp App
   [OK] Core App
   [OK] Payment App

[MIDDLEWARE] MIDDLEWARE CONFIGURATION:
   [OK] CSRF Middleware
   [OK] CORS Middleware

==========================================================================================
[OK] WHATSAPP WEBHOOK FULLY CONFIGURED - READY TO RECEIVE MESSAGES

[NEXT] Next Steps:
   [OK] Webhook is ready to receive messages from Meta Cloud API
   [OK] Monitor logs for incoming messages at: /logs/
   [OK] Test webhook: Use Meta App Dashboard -> Webhooks section
==========================================================================================
```

## How to Use

### Local Development

Run the deployment status check to verify configuration:

```bash
cd backend
python log_whatsapp_webhook_status.py
```

### Production Deployment (Render)

The `render.yaml` configuration automatically:

1. Runs database migrations: `python manage.py migrate`
2. Logs webhook status: `python log_whatsapp_webhook_status.py`
3. Starts the server: `gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT`

All logs are displayed in the Render deployment logs.

### Manual Deployment

If deploying manually, run before starting the server:

```bash
cd backend
python manage.py migrate
python log_whatsapp_webhook_status.py
python manage.py runserver
```

## Log Locations

### Development Server
- Terminal/Console output during `python manage.py runserver`

### Production (Render)
- **Render Dashboard** → Your Service → **Logs** tab
- Search for "WhatsApp" to find all webhook-related logs

### Local Logs
- Check `backend/logs/` directory if logging to file is configured

## Key Indicators

### [OK] Green Status (Ready)
- Configuration is correct
- Feature is active and working
- Webhook is ready to receive messages

### [WARN] Yellow Warnings
- Configuration is missing but optional
- Feature may not work as expected
- Check environment variables

### [ERROR] Red Status (Error)
- Configuration is missing and required
- Feature will not work
- Must be fixed before deployment

## Environment Variables Required

For full WhatsApp webhook functionality, set these environment variables:

- `META_VERIFY_TOKEN` - Token for webhook verification (from Meta App Dashboard)
- `META_APP_SECRET` - App secret for signature verification (from Meta App Dashboard)
- `WEBHOOK_SECRET` - Alternative webhook secret (if using custom implementation)

## Files Modified

1. **[whatsapp/apps.py](whatsapp/apps.py)** - WhatsApp app initialization logging
2. **[backend/wsgi.py](backend/wsgi.py)** - WSGI deployment logging
3. **[core/apps.py](core/apps.py)** - Core app initialization logging
4. **[manage.py](manage.py)** - Migration logging
5. **[log_whatsapp_webhook_status.py](log_whatsapp_webhook_status.py)** - Deployment status script
6. **[../render.yaml](../render.yaml)** - Updated deployment configuration

## Troubleshooting

### No logs appearing?

1. Check that logging is configured in Django settings
2. Verify the app is installed in `INSTALLED_APPS`
3. Check Render dashboard logs if deployed

### Webhook not receiving messages?

1. Run `python log_whatsapp_webhook_status.py` to check configuration
2. Verify `META_VERIFY_TOKEN` and `META_APP_SECRET` in environment
3. Check that webhook URL is correctly configured in Meta App Dashboard
4. Ensure HTTPS is being used (required by Meta)

### "Not configured" warnings?

Set the missing environment variables:
- In **local development**: Add to `.env` file
- In **Render**: Add to Environment Variables in service settings
- In **other platforms**: Follow your platform's env var configuration process
