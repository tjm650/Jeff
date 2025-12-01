"""
Custom middleware for Jeff Platform
"""

import json
import logging
import os
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """Enhanced security middleware"""
    
    def process_request(self, request):
        """Process incoming requests for security checks"""
        # Rate limiting for webhook endpoints
        # Keep this lightweight: we only rate‑limit POST requests hitting webhook
        # style endpoints to protect against abuse and accidental loops.
        if request.method == 'POST' and request.path.startswith('/webhook/'):
            client_ip = self.get_client_ip(request)
            if self.is_rate_limited(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip} on webhook endpoint")
                return JsonResponse({
                    'error': 'Rate limit exceeded'
                }, status=429)
        
        # Validate content type for POST requests
        if request.method == 'POST' and request.content_type:
            if not request.content_type.startswith(('application/json', 'application/x-www-form-urlencoded', 'multipart/form-data')):
                logger.warning(f"Invalid content type: {request.content_type} from {self.get_client_ip(request)}")
                return JsonResponse({
                    'error': 'Invalid content type'
                }, status=400)
        
        return None

    def process_response(self, request, response):
        """Add security headers to responses"""
        # Content Security Policy (configurable via environment)
        csp_enabled = os.getenv('CSP_ENABLED', 'True').lower() == 'true'
        if csp_enabled:
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.paynow.co.zw; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.paynow.co.zw; "
                "frame-src 'self' https://js.paynow.co.zw; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self';"
            )
            response['Content-Security-Policy'] = csp_policy

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_rate_limited(self, ip, max_requests=20, window_minutes=5):
        """Check if IP is rate limited"""
        cache_key = f"rate_limit_ip_{ip}"
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= max_requests:
            return True
        
        cache.set(cache_key, current_requests + 1, window_minutes * 60)
        return False

class InputValidationMiddleware(MiddlewareMixin):
    """Input validation middleware"""
    
    def process_request(self, request):
        """Validate input data"""
        if request.method == 'POST':
            # Check request size
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length and int(content_length) > 16 * 1024 * 1024:  # 16MB
                logger.warning(f"Request too large: {content_length} bytes from {self.get_client_ip(request)}")
                return JsonResponse({
                    'error': 'Request too large'
                }, status=413)
            
            # Validate JSON for API endpoints
            if request.path.startswith('/api/') and request.content_type == 'application/json':
                try:
                    if hasattr(request, '_body'):
                        json.loads(request.body.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"Invalid JSON from {self.get_client_ip(request)}: {str(e)}")
                    return JsonResponse({
                        'error': 'Invalid JSON'
                    }, status=400)
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class LoggingMiddleware(MiddlewareMixin):
    """Enhanced logging middleware"""
    
    def process_request(self, request):
        """Log incoming requests"""
        # Temporarily disable webhook logging to debug duplication issue
        if request.path.startswith(('/api/')):
            logger.info(f"Request: {request.method} {request.path} from {self.get_client_ip(request)}")
        return None
    
    def process_response(self, request, response):
        """Log responses"""
        # Temporarily disable webhook response logging to debug duplication issue
        if request.path.startswith(('/api/')):
            logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
