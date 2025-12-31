"use client";

import React, { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import Link from 'next/link';

export default function PaymentSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Verifying payment...');

  useEffect(() => {
    if (!sessionId) {
      setStatus('error');
      setMessage('Invalid session ID');
      return;
    }

    const verifyPayment = async () => {
      try {
        const response = await fetch(`/api/check-payment-status?session_id=${sessionId}`);
        const data = await response.json();

        if (data.status === 'success') {
          setStatus('success');
          setMessage('Payment successful! Redirecting to chat...');
          // Delay redirect slightly to show success message
          setTimeout(() => {
            router.push('/chat');
          }, 2000);
        } else if (data.status === 'pending') {
          // If pending, maybe retry or tell user
           setMessage('Payment is still pending. Please wait...');
           setTimeout(verifyPayment, 2000); // Poll
        } else {
          setStatus('error');
          setMessage('Payment failed or was incomplete.');
        }
      } catch (err) {
        console.error(err);
        setStatus('error');
        setMessage('Error verifying payment.');
      }
    };

    verifyPayment();
  }, [sessionId, router]);

  return (
    <main className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-8 justify-center items-center text-center">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl max-w-md w-full">
        <div className="flex justify-center mb-6">
          {status === 'loading' && <Loader2 className="w-16 h-16 text-blue-600 animate-spin" />}
          {status === 'success' && <CheckCircle className="w-16 h-16 text-green-500" />}
          {status === 'error' && <XCircle className="w-16 h-16 text-red-500" />}
        </div>
        
        <h2 className="text-2xl font-bold text-white mb-2">
          {status === 'loading' && 'Processing'}
          {status === 'success' && 'Success!'}
          {status === 'error' && 'Error'}
        </h2>
        
        <p className="text-slate-400 mb-6">{message}</p>

        {status === 'error' && (
          <Link 
            href="/payment"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-500 transition-colors"
          >
            Try Again
          </Link>
        )}
        
         {status === 'success' && (
          <Link 
            href="/chat"
            className="inline-block px-6 py-3 bg-green-600 text-white rounded-xl hover:bg-green-500 transition-colors"
          >
            Go to Chat Now
          </Link>
        )}
      </div>
    </main>
  );
}
