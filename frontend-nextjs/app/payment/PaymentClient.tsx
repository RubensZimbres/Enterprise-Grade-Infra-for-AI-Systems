"use client";

import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout
} from '@stripe/react-stripe-js';
import { Loader2, AlertCircle } from 'lucide-react';

interface PaymentClientProps {
  publishableKey: string;
}

export default function PaymentClient({ publishableKey }: PaymentClientProps) {
  const [stripePromise] = useState(() => loadStripe(publishableKey));
  const [email, setEmail] = useState('');
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [clientSecret, setClientSecret] = useState<string | null>(null);

  const fetchClientSecret = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create checkout session');
      }

      const data = await response.json();
      setClientSecret(data.client_secret);
      setStep(2);
      return data.client_secret;
    } catch (err: any) {
      setError(err.message);
      setIsLoading(false);
      return null;
    }
  };

  const handleEmailSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) {
      setError('Email is required');
      return;
    }
    fetchClientSecret();
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Step Indicator */}
      <div className="flex justify-center mb-8">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'}`}>1</div>
        <div className={`w-12 h-1 mt-3.5 mx-2 ${step >= 2 ? 'bg-blue-600' : 'bg-slate-800'}`}></div>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-800 text-slate-400'}`}>2</div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-xl">
        <div className="mb-6 text-center">
          <h2 className="text-2xl font-bold text-white mb-2">Payment Details</h2>
          <p className="text-slate-400">Total: <span className="text-white font-semibold">$36.00 USD</span></p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
        )}

        {step === 1 && (
          <form onSubmit={handleEmailSubmit} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="email" className="block text-sm font-medium text-slate-300">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-600/50 transition-all placeholder:text-slate-500"
                placeholder="you@example.com"
                required
              />
              <p className="text-xs text-slate-500">Your data will not be shared.</p>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-4 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                'Pay with Card'
              )}
            </button>
          </form>
        )}

        {step === 2 && clientSecret && (
          <EmbeddedCheckoutProvider
            stripe={stripePromise}
            options={{ clientSecret }}
          >
            <EmbeddedCheckout className="bg-slate-800 rounded-xl" />
          </EmbeddedCheckoutProvider>
        )}
      </div>
    </div>
  );
}
