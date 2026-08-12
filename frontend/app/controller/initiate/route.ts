import { NextRequest, NextResponse } from 'next/server';

interface PaymentResponse {
  success: boolean;
  reference?: string;
  message?: string;
  amount?: number;
  currency?: string;
}

interface PaymentPayload {
  [key: string]: unknown;
}

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
    this.requestTimes = this.requestTimes.filter(time => time > oneMinuteAgo);
    if (this.requestTimes.length >= this.maxRequestsPerMinute) {
      console.warn('Client-side rate limit exceeded');
      return false;
    }
    this.requestTimes.push(now);
    return true;
  }

  private async makeRequest(url: string, options: RequestInit, retryCount = 0): Promise<Response> {
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
      if (error instanceof Error && error.name === 'AbortError') throw new Error('Request timeout');
      if (retryCount < this.maxRetries && error instanceof TypeError) {
        console.warn(`Request failed, retrying (${retryCount + 1}/${this.maxRetries}):`, error);
        await this.delay(1000 * (retryCount + 1));
        return this.makeRequest(url, options, retryCount + 1);
      }
      throw error;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private validatePaymentResponse(data: unknown): PaymentResponse {
    if (typeof data !== 'object' || data === null) throw new Error('Invalid response format');
    const value = data as PaymentPayload;
    const response: PaymentResponse = {
      success: Boolean(value.success),
      reference: typeof value.reference === 'string' ? value.reference : undefined,
      message: typeof value.message === 'string' ? value.message : undefined,
      amount: typeof value.amount === 'number' ? value.amount : undefined,
      currency: typeof value.currency === 'string' ? value.currency : undefined,
    };
    if (response.success && !response.reference) throw new Error('Payment reference missing from successful response');
    if (response.amount !== undefined && response.amount < 0) throw new Error('Invalid payment amount');
    return response;
  }

  async post(endpoint: string, body: PaymentPayload): Promise<PaymentResponse> {
    if (!this.checkRateLimit()) throw new Error('Rate limit exceeded. Please try again later.');
    try {
      const response = await this.makeRequest(`${this.baseUrl}${endpoint}`, {
        method: 'POST',
        body: JSON.stringify(body),
      });
      const data: unknown = await response.json();
      if (!response.ok) {
        console.error('API Error:', { status: response.status, statusText: response.statusText, data });
        throw new Error('Transaction failed. Please try again');
      }
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
    if (!whatsapp_number || !payment_number) return NextResponse.json({ success: false, message: 'WhatsApp number and payment number are required' }, { status: 400 });
    if (typeof whatsapp_number !== 'string' || typeof payment_number !== 'string') return NextResponse.json({ success: false, message: 'Invalid input format' }, { status: 400 });
    if (!/^(\+263|0)[0-9]{9,10}$/.test(whatsapp_number)) return NextResponse.json({ success: false, message: 'Invalid WhatsApp number format' }, { status: 400 });
    const data = await apiClient.post('/api/payment/v1/initiate_paynow/', { whatsapp_number, payment_number });
    return NextResponse.json(data);
  } catch (error) {
    console.error('Payment initiation error:', error);
    let message = 'Internal server error';
    let status = 500;
    if (error instanceof Error) {
      if (error.message.includes('timeout')) { message = 'Request timed out. Please try again.'; status = 408; }
      else if (error.message.includes('network') || error.message.includes('fetch')) { message = 'Network error. Please check your connection and try again.'; status = 503; }
      else if (error.message.includes('Invalid response format')) { message = 'Invalid response from payment service.'; status = 502; }
      else message = error.message;
    }
    return NextResponse.json({ success: false, message }, { status });
  }
}