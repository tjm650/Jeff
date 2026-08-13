import { NextRequest, NextResponse } from 'next/server';

interface PaymentResponse {
  success: boolean;
  reference?: string;
  paynow_reference?: string;
  poll_url?: string | null;
  redirect_url?: string | null;
  transaction_id?: string;
  message?: string;
  instructions?: string;
  amount?: string | number;
  currency?: string;
}

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const MAX_RETRIES = parseInt(process.env.API_MAX_RETRIES || '2');
const TIMEOUT = parseInt(process.env.API_REQUEST_TIMEOUT_MS || '10000');

async function callPaymentFunction(body: Record<string, unknown>, retry = 0): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);

  try {
    const response = await fetch(`${SUPABASE_URL}/functions/v1/payment-initiate`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        apikey: SUPABASE_ANON_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);

    if (retry < MAX_RETRIES && error instanceof TypeError) {
      await new Promise(resolve => setTimeout(resolve, 1000 * (retry + 1)));
      return callPaymentFunction(body, retry + 1);
    }

    throw error;
  }
}

export async function POST(request: NextRequest) {
  try {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
      return NextResponse.json(
        { success: false, message: 'Payment service is not configured.' },
        { status: 500 },
      );
    }

    const { whatsapp_number, payment_number } = await request.json();

    if (!whatsapp_number || !payment_number) {
      return NextResponse.json(
        { success: false, message: 'WhatsApp number and payment number are required' },
        { status: 400 },
      );
    }

    if (typeof whatsapp_number !== 'string' || typeof payment_number !== 'string') {
      return NextResponse.json(
        { success: false, message: 'Invalid input format' },
        { status: 400 },
      );
    }

    if (!/^(\+263|0)[0-9]{9,10}$/.test(whatsapp_number)) {
      return NextResponse.json(
        { success: false, message: 'Invalid WhatsApp number format' },
        { status: 400 },
      );
    }

    const response = await callPaymentFunction({
      whatsapp_number,
      payment_number,
    });

    const data: PaymentResponse = await response.json().catch(() => ({
      success: false,
      message: 'Invalid response from payment service.',
    }));

    if (!response.ok) {
      return NextResponse.json(
        { success: false, message: data.message || 'Transaction failed. Please try again' },
        { status: response.status >= 500 ? 502 : response.status },
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Payment initiation error:', error);

    let message = 'Internal server error';
    let status = 500;

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        message = 'Request timed out. Please try again.';
        status = 408;
      } else if (error.message.includes('fetch')) {
        message = 'Network error. Please check your connection and try again.';
        status = 503;
      }
    }

    return NextResponse.json({ success: false, message }, { status });
  }
}
