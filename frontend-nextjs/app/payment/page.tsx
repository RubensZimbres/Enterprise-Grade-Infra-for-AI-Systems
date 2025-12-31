import React from 'react';
import { getSecret } from '@/lib/secrets';
import PaymentClient from './PaymentClient';
import { ShieldCheck } from 'lucide-react';

export default async function PaymentPage() {
  const publishableKey = await getSecret('STRIPE_PUBLISHABLE_KEY');

  if (!publishableKey) {
    return (
      <main className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-8 justify-center items-center text-center">
        <div className="p-4 bg-red-500/10 rounded-full mb-4">
          <ShieldCheck className="w-12 h-12 text-red-500" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">Configuration Error</h1>
        <p className="text-slate-400">
          Payment system is currently unavailable. Please check system configuration.
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 flex flex-col items-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="mb-8 text-center">
        <div className="flex justify-center mb-4">
          <div className="p-3 bg-blue-600 rounded-xl">
            <ShieldCheck className="w-8 h-8 text-white" />
          </div>
        </div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Secure Checkout</h1>
        <p className="mt-2 text-slate-400">Initialize your secure session</p>
      </div>
      
      <PaymentClient publishableKey={publishableKey} />
    </main>
  );
}
