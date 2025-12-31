import { NextRequest, NextResponse } from 'next/server';
import { GoogleAuth } from 'google-auth-library';
import CircuitBreaker from 'opossum';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const auth = new GoogleAuth();

// --- Circuit Breaker Configuration ---
const breakerOptions = {
  timeout: 15000, // Timeout after 15 seconds (Backend is streaming, but initial connection should be fast)
  errorThresholdPercentage: 50, // Trip if 50% of requests fail
  resetTimeout: 10000, // Wait 10 seconds before trying again (Half-Open)
};

// Function to wrap with Circuit Breaker
async function fetchBackend(url: string, options: RequestInit) {
  const response = await fetch(url, options);
  if (!response.ok) {
     // Throwing error triggers the failure count in Opossum
     throw new Error(`Backend Error: ${response.status} ${response.statusText}`);
  }
  return response;
}

// Initialize Breaker (Global scope to persist across warm invocations)
const breaker = new CircuitBreaker(fetchBackend, breakerOptions);

breaker.fallback(() => {
  return new Response(
    JSON.stringify({ error: 'Service Unavailable (Circuit Open). Please try again later.' }),
    { status: 503, headers: { 'Content-Type': 'application/json' } }
  );
});

// Logging for visibility
breaker.on('open', () => console.warn('🔴 Circuit Breaker OPEN: Backend is failing'));
breaker.on('halfOpen', () => console.log('🟡 Circuit Breaker HALF-OPEN: Testing backend'));
breaker.on('close', () => console.log('🟢 Circuit Breaker CLOSED: Backend is healthy'));

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Use server-side only env var (not NEXT_PUBLIC_)
    const backendUrl = process.env.BACKEND_URL;

    if (!backendUrl) {
      console.error('BACKEND_URL environment variable is not configured');
      return NextResponse.json(
        { error: 'Backend URL not configured.' },
        { status: 500 }
      );
    }

    // Validate request body
    if (!body.message || typeof body.message !== 'string') {
      return NextResponse.json(
        { error: 'Invalid request: message is required' },
        { status: 400 }
      );
    }

    // Extract User Identity Token (Firebase) from Client Request
    const userAuthToken = req.headers.get('Authorization');
    if (!userAuthToken) {
        return NextResponse.json(
            { error: 'Unauthorized: Missing User Token' },
            { status: 401 }
        );
    }

    // Payment validation is now handled by the backend-agent
    // using the X-Firebase-Token and Cloud SQL check.

    const firebaseToken = userAuthToken.replace('Bearer ', '');

    console.log(`Forwarding request to: ${backendUrl}/stream`);

    // Get Service-to-Service OIDC auth headers
    let serviceAuthHeaders = {};
    if (!backendUrl.includes('localhost')) {
      try {
        const client = await auth.getIdTokenClient(backendUrl);
        serviceAuthHeaders = await client.getRequestHeaders();
        console.log('Generated Service-to-Service OIDC token');
      } catch (err) {
        console.error('Failed to get service-to-service ID token:', err);
      }
    }

    const fetchOptions: RequestInit = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...serviceAuthHeaders,
        'X-Firebase-Token': firebaseToken,
      },
      body: JSON.stringify(body),
    };

    // --- Execute with Circuit Breaker ---
    try {
        const response = await breaker.fire(`${backendUrl}/stream`, fetchOptions);
        
        // If fallback triggered (Response object from fallback), return it
        if (response.status === 503 && !response.body) { 
             // Opossum fallback might return a Response-like object depending on implementation
             // But here our fallback returns a standard Response
             return response;
        }

        if (!response.body) {
            return NextResponse.json(
                { error: 'Empty response from backend' },
                { status: 502 }
            );
        }

        // Proxy the stream back to the client
        return new Response(response.body, {
            status: 200,
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            },
        });

    } catch (err: any) {
        console.error('Circuit Breaker Error:', err);
        if (err.code === 'EOPEN') {
             return NextResponse.json(
                { error: 'Service Unavailable (Circuit Breaker Open)' },
                { status: 503 }
            );
        }
        return NextResponse.json(
            { error: `Backend Request Failed: ${err.message}` },
            { status: 500 }
        );
    }

  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS preflight
export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
