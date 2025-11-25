import { NextRequest, NextResponse } from 'next/server';

// Payment response validation schema
interface PaymentResponse {
  success: boolean;
  reference?: string;
  message?: string;
  amount?: number;
  currency?: string;
}

// API client with security features
class SecureAPIClient {
  private apiKey: string;
  private baseUrl: string;
  private maxRetries: number;
  private timeout: number;
  private requestTimes: number[] = [];
  private maxRequestsPerMinute: number;

  constructor() {
    this.apiKey = process.env.DJANGO_API_KEY || '';
    this.baseUrl = process.env.DJANGO_API_URL || '';
    this.maxRetries = parseInt(process.env.API_MAX_RETRIES || '3');
    this.timeout = parseInt(process.env.API_REQUEST_TIMEOUT_MS || '10000');
    this.maxRequestsPerMinute = parseInt(process.env.API_RATE_LIMIT_REQUESTS_PER_MINUTE || '30');
  }

  private checkRateLimit(): boolean {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove requests older than 1 minute
    this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);

    // Check if under limit
    if (this.requestTimes.length >= this.maxRequestsPerMinute) {
      console.warn('Client-side rate limit exceeded');
      return false;
    }

    // Record this request
    this.requestTimes.push(now);
    return true;
  }

  private async makeRequest(url: string, options: RequestInit, retryCount: number = 0): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...options.headers,
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json',
        },
      });

      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }

      // Retry logic for network errors
      if (retryCount < this.maxRetries && this.isRetryableError(error)) {
        console.warn(`Request failed, retrying (${retryCount + 1}/${this.maxRetries}):`, error);
        await this.delay(1000 * (retryCount + 1)); // Exponential backoff
        return this.makeRequest(url, options, retryCount + 1);
      }

      throw error;
    }
  }

  private isRetryableError(error: any): boolean {
    // Retry on network errors, timeouts, 5xx errors
    return error instanceof TypeError || (error instanceof Response && error.status >= 500);
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private validatePaymentResponse(data: any): PaymentResponse {
    // Validate payment response structure
    if (typeof data !== 'object' || data === null) {
      throw new Error('Invalid response format');
    }

    const response: PaymentResponse = {
      success: Boolean(data.success),
      reference: typeof data.reference === 'string' ? data.reference : undefined,
      message: typeof data.message === 'string' ? data.message : undefined,
      amount: typeof data.amount === 'number' ? data.amount : undefined,
      currency: typeof data.currency === 'string' ? data.currency : undefined,
    };

    // Additional validation for payment data
    if (response.success && !response.reference) {
      throw new Error('Payment reference missing from successful response');
    }

    if (response.amount !== undefined && response.amount < 0) {
      throw new Error('Invalid payment amount');
    }

    return response;
  }

  async post(endpoint: string, body: any): Promise<PaymentResponse> {
    // Check client-side rate limit
    if (!this.checkRateLimit()) {
      throw new Error('Rate limit exceeded. Please try again later.');
    }

    const url = `${this.baseUrl}${endpoint}`;

    try {
      const response = await this.makeRequest(url, {
        method: 'POST',
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        console.error('API Error:', {
          status: response.status,
          statusText: response.statusText,
          data
        });
        // throw new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
        throw new Error(`Transaction failed. Please try again`)
      }

      // Validate response data
      return this.validatePaymentResponse(data);

    } catch (error) {
      console.error('Secure API Client Error:', error);
      throw error;
    }
  }
}

const apiClient = new SecureAPIClient();

export async function POST(request: NextRequest) {
  try {
    const { whatsapp_number, payment_number } = await request.json();

    // Validate input
    if (!whatsapp_number || !payment_number) {
      return NextResponse.json(
        { success: false, message: 'WhatsApp number and payment number are required' },
        { status: 400 }
      );
    }

    // Additional input validation
    if (typeof whatsapp_number !== 'string' || typeof payment_number !== 'string') {
      return NextResponse.json(
        { success: false, message: 'Invalid input format' },
        { status: 400 }
      );
    }

    // Validate phone number format (basic)
    if (!/^(\+263|0)[0-9]{9,10}$/.test(whatsapp_number)) {
      return NextResponse.json(
        { success: false, message: 'Invalid WhatsApp number format' },
        { status: 400 }
      );
    }

    // Call Django backend API with security features
    const data = await apiClient.post('/api/payment/v1/initiate_paynow/', {
      whatsapp_number,
      payment_number,
    });

    return NextResponse.json(data);

  } catch (error) {
    console.error('Payment initiation error:', error);

    // Provide user-friendly error messages
    let message = 'Internal server error';
    let status = 500;

    if (error instanceof Error) {
      if (error.message.includes('timeout')) {
        message = 'Request timed out. Please try again.';
        status = 408;
      } else if (error.message.includes('network') || error.message.includes('fetch')) {
        message = 'Network error. Please check your connection and try again.';
        status = 503;
      } else if (error.message.includes('Invalid response format')) {
        message = 'Invalid response from payment service.';
        status = 502;
      } else {
        message = error.message;
      }
    }

    return NextResponse.json(
      { success: false, message },
      { status }
    );
  }
}