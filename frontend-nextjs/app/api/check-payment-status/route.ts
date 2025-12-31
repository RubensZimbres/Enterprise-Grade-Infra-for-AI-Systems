import { NextResponse } from 'next/server';
import { getStripe } from '@/lib/stripe';
import { cookies } from 'next/headers';

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const sessionId = searchParams.get('session_id');

  if (!sessionId) {
    return NextResponse.json({ error: 'Session ID is required' }, { status: 400 });
  }

  try {
    const stripe = await getStripe();
    const session = await stripe.checkout.sessions.retrieve(sessionId);

    if (session.status === 'complete' && session.payment_status === 'paid') {
      // Payment successful
      
      // Set a cookie to indicate payment success (Basic implementation)
      // In a real app, use a JWT or secure session store
      cookies().set('payment_completed', 'true', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        path: '/',
        maxAge: 60 * 60 * 24 * 30, // 30 days
      });

      return NextResponse.json({
        status: 'success',
        customer_email: session.customer_email,
        order_id: session.client_reference_id
      });
    } else if (session.status === 'open') {
      return NextResponse.json({ status: 'pending' });
    } else {
      return NextResponse.json({ status: 'failed' });
    }
  } catch (error: any) {
    console.error('Error checking payment status:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
