import React from 'react';
import { Database, ShieldAlert, Sparkles, Network } from 'lucide-react';
import { HealthResponse } from '../types';

interface HeaderProps {
  health: HealthResponse | null;
}

export const Header: React.FC<HeaderProps> = ({ health }) => {
  const isConnected = health?.neo4j_connected;

  return (
    <header className="bg-surface border-b border-borderDark px-6 py-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-l-4 border-l-amberAccent">
      <div>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-amberAccent/10 border border-amberAccent/30 text-amberAccent">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              AI-Powered Criminal Network Analysis
            </h1>
            <p className="text-xs text-textMuted mt-0.5">
              Case <span className="text-tealAccent font-semibold font-mono">NCRB-2026-0847</span> — Fused FIR, CDR &amp; financial transaction intelligence
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border ${
            isConnected
              ? 'bg-emerald-950/40 border-emerald-600/40 text-emerald-400'
              : 'bg-amber-950/40 border-amber-600/40 text-amber-400'
          }`}
          title={health?.neo4j_uri || 'Neo4j Database'}
        >
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <Database className="w-3.5 h-3.5" />
          <span>{isConnected ? 'NEO4J LIVE' : 'OFFLINE MOCK MODE'}</span>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface border border-borderDark text-xs font-mono text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-amberAccent" />
          <span>GEMINI AI ACTIVE</span>
        </div>
      </div>
    </header>
  );
};

