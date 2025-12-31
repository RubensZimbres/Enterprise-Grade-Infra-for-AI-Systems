'use client';

import { useState } from 'react';
import { signInWithPopup, GoogleAuthProvider, OAuthProvider, signInWithEmailAndPassword } from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (providerName: string) => {
    try {
      let provider;
      if (providerName === 'google') {
        provider = new GoogleAuthProvider();
      } else if (providerName === 'microsoft') {
        provider = new OAuthProvider('microsoft.com');
      }

      if (provider) {
        await signInWithPopup(auth, provider);
        router.push('/');
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await signInWithEmailAndPassword(auth, email, password);
      router.push('/');
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-slate-900 p-6 shadow-xl border border-slate-800">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-slate-100">Welcome Back</h2>
          <p className="mt-2 text-slate-400">Sign in to your account</p>
        </div>

        {error && <div className="text-red-500 text-sm text-center">{error}</div>}

        <div className="space-y-4">
          <button
            onClick={() => handleLogin('google')}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-white px-4 py-2 text-slate-900 hover:bg-slate-200"
          >
            Sign in with Google
          </button>
          
          <button
            onClick={() => handleLogin('microsoft')}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-[#00a4ef] px-4 py-2 text-white hover:bg-[#0078d4]"
          >
            Sign in with Microsoft
          </button>
        </div>

        <div className="relative flex items-center justify-center border-t border-slate-800 py-4">
          <span className="absolute bg-slate-900 px-2 text-sm text-slate-500">Or continue with</span>
        </div>

        <form onSubmit={handleEmailLogin} className="space-y-4">
          <div>
            <input
              type="email"
              placeholder="Email address"
              className="w-full rounded-md bg-slate-800 border border-slate-700 px-4 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <input
              type="password"
              placeholder="Password"
              className="w-full rounded-md bg-slate-800 border border-slate-700 px-4 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 font-medium"
          >
            Sign In with Email
          </button>
        </form>
      </div>
    </div>
  );
}
