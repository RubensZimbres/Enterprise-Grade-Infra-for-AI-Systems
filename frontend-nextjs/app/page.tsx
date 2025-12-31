import React from 'react';
import Link from 'next/link';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export default function LandingPage() {
  return (
    <main className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-8 justify-center items-center">
      <div className="flex flex-col items-center gap-6 text-center">
        <div className="p-4 bg-blue-600 rounded-2xl shadow-lg shadow-blue-600/20">
          <ShieldCheck className="w-16 h-16 text-white" />
        </div>
        
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight text-white">Enterprise AI Agent</h1>
          <p className="text-lg text-slate-400">Secure RAG Pipeline v2.0</p>
        </div>

        <div className="max-w-md text-slate-300 leading-relaxed">
          <p>
            Access our secure knowledge base and neural core analysis. 
            A one-time payment is required to initialize your secure session.
          </p>
        </div>

        <Link 
          href="/payment"
          className="group flex items-center gap-2 px-8 py-4 bg-blue-600 text-white rounded-full font-semibold text-lg hover:bg-blue-500 transition-all shadow-lg hover:shadow-blue-600/25"
        >
          Initialize Access
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>

      <footer className="absolute bottom-8 text-center">
        <p className="text-[10px] text-slate-600 uppercase tracking-[0.2em]">
          End-to-End Encrypted • DLP Guardrails Active
        </p>
      </footer>
    </main>
  );
}
