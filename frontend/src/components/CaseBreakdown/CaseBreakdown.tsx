import React, { useState, useEffect } from 'react';
import { FileText, ShieldAlert, AlertTriangle, CheckCircle, Printer, Download, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { CaseBreakdownResponse } from '../../types';

export const CaseBreakdown: React.FC = () => {
  const [data, setData] = useState<CaseBreakdownResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchBreakdown = async () => {
      try {
        const res = await api.getCaseBreakdown();
        setData(res);
      } catch (err) {
        console.error('Failed to load case breakdown:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchBreakdown();
  }, []);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-amberAccent font-mono text-sm gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Compiling executive case intelligence report...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-8 text-center text-textMuted font-mono text-sm">
        Unable to generate case breakdown dossier at this moment.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto print:bg-white print:text-black">
      {/* Action Bar */}
      <div className="flex items-center justify-between bg-surface border border-borderDark rounded-lg px-5 py-3 print:hidden">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-amberAccent" />
          <span className="text-xs font-mono font-semibold text-white uppercase tracking-wider">
            Official Case Intelligence Dossier
          </span>
        </div>
        <button
          onClick={handlePrint}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-background hover:bg-slate-800 border border-borderDark text-xs font-mono text-slate-200 rounded transition"
        >
          <Printer className="w-3.5 h-3.5 text-amberAccent" /> Print / Save as PDF
        </button>
      </div>

      {/* Case Header Card */}
      <div className="bg-surface border border-borderDark rounded-lg p-6 border-l-4 border-l-amberAccent">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono font-bold text-tealAccent">
            CLASSIFIED // LAW ENFORCEMENT SENSITIVE
          </span>
          <span className="text-xs font-mono text-textMuted">Case Ref: {data.case_id}</span>
        </div>
        <h2 className="text-xl font-bold font-mono text-white mb-2">{data.title}</h2>
        <p className="text-xs text-slate-300 leading-relaxed font-sans">{data.summary}</p>
      </div>

      {/* Key Suspects Grid */}
      <div className="bg-surface border border-borderDark rounded-lg p-5">
        <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-textMuted mb-4 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amberAccent" /> Key High-Threat Suspects
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {data.key_suspects.map((s, idx) => (
            <div
              key={idx}
              className="bg-background border border-borderDark p-3.5 rounded flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <span className="font-mono text-sm font-bold text-white block">{s.name}</span>
                  <span className="text-xs font-mono text-tealAccent">{s.role}</span>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                    s.threat_level === 'CRITICAL'
                      ? 'bg-alertRed/20 text-alertRed border border-alertRed/30'
                      : 'bg-amberAccent/20 text-amberAccent border border-amberAccent/30'
                  }`}
                >
                  {s.threat_level}
                </span>
              </div>
              <p className="text-xs text-textMuted font-sans">{s.notes}</p>
            </div>
          ))}
        </div>
      </div>

      {/* High-Risk Cells & Anomalies */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Cells */}
        <div className="bg-surface border border-borderDark rounded-lg p-5">
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-textMuted mb-3">
            Operational Cells Under Target
          </h3>
          <div className="space-y-2">
            {data.high_risk_cells.map((cell) => (
              <div
                key={cell.cell_id}
                className="bg-background border border-borderDark p-3 rounded flex items-center justify-between text-xs font-mono"
              >
                <div>
                  <span className="font-bold text-slate-200 block">Cell #{cell.cell_id}</span>
                  <span className="text-textMuted">Commander: {cell.leader}</span>
                </div>
                <div className="text-right">
                  <span className="text-amberAccent font-bold">PR: {cell.influence_score}</span>
                  <span className="block text-[10px] text-tealAccent">{cell.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Anomalies */}
        <div className="bg-surface border border-borderDark rounded-lg p-5">
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-textMuted mb-3 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-alertRed" /> Flagged Surveillance Triggers
          </h3>
          <div className="space-y-2">
            {data.anomalies_detected.map((anom, idx) => (
              <div
                key={idx}
                className="bg-background border border-borderDark p-3 rounded text-xs font-mono"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-slate-200">{anom.entity}</span>
                  <span className="text-[10px] uppercase text-textMuted">{anom.type}</span>
                </div>
                <div className="text-alertRed font-medium">{anom.signature}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tactical Recommendations */}
      <div className="bg-surface border border-borderDark rounded-lg p-5 border-l-4 border-l-tealAccent">
        <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-tealAccent mb-3 flex items-center gap-1.5">
          <CheckCircle className="w-4 h-4" /> Tactical Intelligence Directives
        </h3>
        <ul className="space-y-2.5">
          {data.recommendations.map((rec, idx) => (
            <li key={idx} className="text-xs text-slate-300 font-sans flex items-start gap-2.5">
              <span className="w-1.5 h-1.5 rounded-full bg-tealAccent shrink-0 mt-1.5"></span>
              <span>{rec}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

