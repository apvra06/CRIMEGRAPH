import React from 'react';
import { Users, Grid, AlertTriangle, Crown, RefreshCw, Layers } from 'lucide-react';
import { CaseOverviewStats } from '../types';

interface SidebarProps {
  stats: CaseOverviewStats | null;
  loading: boolean;
  onRefresh: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ stats, loading, onRefresh }) => {
  return (
    <aside className="w-full lg:w-64 bg-surface border-r border-borderDark flex flex-col p-4 shrink-0">
      <div className="flex items-center justify-between pb-3 mb-4 border-b border-borderDark">
        <span className="text-xs font-mono uppercase tracking-wider text-textMuted font-semibold flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-amberAccent" /> Case File
        </span>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1 rounded hover:bg-slate-800 text-textMuted hover:text-slate-200 transition-colors"
          title="Refresh metrics"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="space-y-3">
        {/* Metric 1: Total Suspects */}
        <div className="bg-background border border-borderDark border-l-2 border-l-amberAccent rounded p-3 transition hover:border-borderDark/80">
          <div className="flex items-center justify-between text-xs text-textMuted font-mono mb-1">
            <span>Total Suspects</span>
            <Users className="w-3.5 h-3.5 text-amberAccent" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {stats ? stats.suspects : '—'}
          </div>
        </div>

        {/* Metric 2: Cells Detected */}
        <div className="bg-background border border-borderDark border-l-2 border-l-tealAccent rounded p-3 transition hover:border-borderDark/80">
          <div className="flex items-center justify-between text-xs text-textMuted font-mono mb-1">
            <span>Cells Detected</span>
            <Grid className="w-3.5 h-3.5 text-tealAccent" />
          </div>
          <div className="text-xl font-bold font-mono text-white">
            {stats ? stats.cells : '—'}
          </div>
        </div>

        {/* Metric 3: Anomalies Flagged */}
        <div className="bg-background border border-borderDark border-l-2 border-l-alertRed rounded p-3 transition hover:border-borderDark/80">
          <div className="flex items-center justify-between text-xs text-textMuted font-mono mb-1">
            <span>Anomalies Flagged</span>
            <AlertTriangle className="w-3.5 h-3.5 text-alertRed" />
          </div>
          <div className="text-xl font-bold font-mono text-alertRed">
            {stats ? stats.anomalies : '—'}
          </div>
        </div>

        {/* Metric 4: Top Influencer */}
        <div className="bg-background border border-borderDark border-l-2 border-l-amberAccent rounded p-3 transition hover:border-borderDark/80">
          <div className="flex items-center justify-between text-xs text-textMuted font-mono mb-1">
            <span>Top Influencer</span>
            <Crown className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-sm font-semibold font-mono text-slate-100 truncate" title={stats?.top_influencer || ''}>
            {stats?.top_influencer || '—'}
          </div>
          {stats?.top_influencer_score && (
            <div className="text-[11px] text-textMuted font-mono mt-0.5">
              Score: {stats.top_influencer_score}
            </div>
          )}
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-borderDark/60 text-xs text-textMuted">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-2">
          Intelligence Feeds
        </div>
        <div className="space-y-1 text-[11px]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>FIR Incident Reports</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-tealAccent"></span>
            <span>Call Detail Records (CDR)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amberAccent"></span>
            <span>Financial Transaction Logs</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

