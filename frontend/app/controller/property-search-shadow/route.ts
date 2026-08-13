import { NextRequest, NextResponse } from 'next/server';

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const DJANGO_API_URL = process.env.DJANGO_API_URL || '';
const TIMEOUT = parseInt(process.env.API_REQUEST_TIMEOUT_MS || '10000');

async function fetchJson(url: string, init: RequestInit) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    const data = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, data };
  } finally {
    clearTimeout(timeoutId);
  }
}

function normalizeId(value: unknown) {
  return String(value ?? '');
}

function djangoIds(data: any): string[] {
  const matches = Array.isArray(data?.matches) ? data.matches : [];
  return matches.map((m: any) => normalizeId(m?.property?.id));
}

function supabaseIds(data: any): string[] {
  const results = Array.isArray(data?.results) ? data.results : [];
  return results.map((r: any) => normalizeId(r?.property?.id));
}

export async function POST(request: NextRequest) {
  try {
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !DJANGO_API_URL) {
      return NextResponse.json(
        { success: false, message: 'Shadow comparison is not configured.' },
        { status: 500 },
      );
    }

    const body = await request.json();
    const requirements = body.requirements ?? body;

    if (!requirements || typeof requirements !== 'object') {
      return NextResponse.json(
        { success: false, message: 'Requirements object is required.' },
        { status: 400 },
      );
    }

    const [django, supabase] = await Promise.all([
      fetchJson(`${DJANGO_API_URL.replace(/\/$/, '')}/api/matching/match/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requirements }),
      }),
      fetchJson(`${SUPABASE_URL}/functions/v1/property-search`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
          apikey: SUPABASE_ANON_KEY,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ requirements, limit: 5 }),
      }),
    ]);

    const djangoIdsList = djangoIds(django.data);
    const supabaseIdsList = supabaseIds(supabase.data);
    const commonIds = djangoIdsList.filter((id) => supabaseIdsList.includes(id));
    const exactOrderMatch =
      djangoIdsList.length === supabaseIdsList.length &&
      djangoIdsList.every((id, index) => id === supabaseIdsList[index]);

    return NextResponse.json({
      success: true,
      production_source: 'django',
      django: {
        ok: django.ok,
        status: django.status,
        ids: djangoIdsList,
        response: django.data,
      },
      supabase: {
        ok: supabase.ok,
        status: supabase.status,
        ids: supabaseIdsList,
        response: supabase.data,
      },
      comparison: {
        django_count: djangoIdsList.length,
        supabase_count: supabaseIdsList.length,
        common_count: commonIds.length,
        overlap_ratio: djangoIdsList.length
          ? Number((commonIds.length / djangoIdsList.length).toFixed(3))
          : 1,
        exact_order_match: exactOrderMatch,
        common_ids: commonIds,
      },
    });
  } catch (error) {
    console.error('Property search shadow comparison error:', error);
    return NextResponse.json(
      { success: false, message: 'Shadow comparison failed.' },
      { status: 500 },
    );
  }
}
