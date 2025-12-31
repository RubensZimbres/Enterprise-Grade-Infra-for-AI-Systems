import { NextResponse } from 'next/server';
import { getStripe } from '@/lib/stripe';
import { headers } from 'next/headers';

export async function POST(req: Request) {
  try {
    const { email } = await req.json();
    
    if (!email) {
      return NextResponse.json({ error: 'Email is required' }, { status: 400 });
    }

    const stripe = await getStripe();
    const headersList = headers();
    const origin = headersList.get('origin') || headersList.get('host') || '';
    // Ensure protocol is present
    const protocol = process.env.NODE_ENV === 'development' ? 'http' : 'https';
    const host = origin.includes('http') ? origin : `${protocol}://${origin}`;

    const orderRef = `order-${Math.floor(Math.random() * 10000000000)}`;

    const session = await stripe.checkout.sessions.create({
      ui_mode: 'embedded',
      payment_method_types: ['card'],
      customer_email: email,
      line_items: [{
        price_data: {
          currency: 'usd',
          product_data: {
            name: 'Sample Product',
          },
          unit_amount: 3600, // $36.00
        },
        quantity: 1,
      }],
      mode: 'payment',
      return_url: `${host}/payment-success?session_id={CHECKOUT_SESSION_ID}`,
      client_reference_id: orderRef,
      metadata: {
        customer_email: email,
        product: 'ai_access'
      },
    });

    return NextResponse.json({
      id: session.id,
      client_secret: session.client_secret,
    });
  } catch (error: any) {
    console.error('Stripe error:', error);
    return NextResponse.json({ error: error.message || 'Internal server error' }, { status: 500 });
  }
}
