import React, { useState, useEffect } from 'react';
import { Crown, Network, AlertOctagon, ArrowUpDown, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { LeadershipItem, IntermediaryItem, AnomalyItem } from '../../types';

export const OverviewDashboard: React.FC = () => {
  const [leaders, setLeaders] = useState<LeadershipItem[]>([]);
  const [intermediaries, setIntermediaries] = useState<IntermediaryItem[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ld, inter, anom] = await Promise.all([
          api.getLeadership(),
          api.getIntermediaries(),
          api.getAnomalies(),
        ]);
        setLeaders(ld);
        setIntermediaries(inter);
        setAnomalies(anom);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12 text-amberAccent font-mono text-sm gap-2">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span>Loading crime intelligence leaderboards...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 1. Cell Leadership Table */}
      <div className="bg-surface border border-borderDark rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-borderDark">
          <Crown className="w-4 h-4 text-amberAccent" />
          <h3 className="text-sm font-bold font-mono text-white">
            Cell Leadership — PageRank by Community
          </h3>
        </div>

        <div className="overflow-x-auto border border-borderDark rounded">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-background text-textMuted uppercase text-[10px] border-b border-borderDark">
              <tr>
                <th className="px-4 py-2.5">#</th>
                <th className="px-4 py-2.5">Person</th>
                <th className="px-4 py-2.5">Community / Cell</th>
                <th className="px-4 py-2.5 text-right">Influence (PageRank)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderDark">
              {leaders.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-2 text-textMuted">{idx + 1}</td>
                  <td className="px-4 py-2 font-semibold text-slate-200">{item.person}</td>
                  <td className="px-4 py-2">
                    <span className="px-2 py-0.5 rounded bg-background border border-borderDark text-[11px] text-tealAccent">
                      Cell #{item.community ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right text-amberAccent font-bold">
                    {item.influence !== null && item.influence !== undefined ? item.influence.toFixed(4) : '—'}
                  </td>
                </tr>
              ))}
              {leaders.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-4 text-center text-textMuted">
                    No leadership records available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 2. Known Intermediaries Table */}
      <div className="bg-surface border border-borderDark rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-borderDark">
          <Network className="w-4 h-4 text-tealAccent" />
          <h3 className="text-sm font-bold font-mono text-white">
            Known Intermediaries — Betweenness Centrality (Top Bridges)
          </h3>
        </div>

        <div className="overflow-x-auto border border-borderDark rounded">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-background text-textMuted uppercase text-[10px] border-b border-borderDark">
              <tr>
                <th className="px-4 py-2.5">#</th>
                <th className="px-4 py-2.5">Person</th>
                <th className="px-4 py-2.5 text-right">Bridge Score (Betweenness)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderDark">
              {intermediaries.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition">
                  <td className="px-4 py-2 text-textMuted">{idx + 1}</td>
                  <td className="px-4 py-2 font-semibold text-slate-200">{item.person}</td>
                  <td className="px-4 py-2 text-right text-tealAccent font-bold">
                    {item.bridge_score !== null && item.bridge_score !== undefined ? item.bridge_score.toFixed(3) : '—'}
                  </td>
                </tr>
              ))}
              {intermediaries.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-4 text-center text-textMuted">
                    No intermediary records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Active Flags Table */}
      <div className="bg-surface border border-borderDark rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4 pb-2 border-b border-borderDark">
          <AlertOctagon className="w-4 h-4 text-alertRed" />
          <h3 className="text-sm font-bold font-mono text-white">
            Active Surveillance Flags &amp; Structural Anomalies
          </h3>
        </div>

        <div className="overflow-x-auto border border-borderDark rounded">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-background text-textMuted uppercase text-[10px] border-b border-borderDark">
              <tr>
                <th className="px-4 py-2.5">#</th>
                <th className="px-4 py-2.5">Entity Type</th>
                <th className="px-4 py-2.5">Target Identifier / Name</th>
                <th className="px-4 py-2.5">Flag Trigger</th>
                <th className="px-4 py-2.5 text-right">Spike Calls</th>
                <th className="px-4 py-2.5 text-right">Sub-₹50k Txns</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderDark">
              {anomalies.map((item, idx) => (
                <tr key={idx} className="bg-alertRed/5 hover:bg-alertRed/10 transition border-l-2 border-l-alertRed">
                  <td className="px-4 py-2 text-textMuted">{idx + 1}</td>
                  <td className="px-4 py-2">
                    <span className="px-2 py-0.5 rounded bg-background border border-borderDark text-[10px] text-slate-300 uppercase">
                      {item.type}
                    </span>
                  </td>
                  <td className="px-4 py-2 font-bold text-slate-100">{item.name}</td>
                  <td className="px-4 py-2 text-alertRed font-medium">{item.flag}</td>
                  <td className="px-4 py-2 text-right text-slate-300 font-bold">
                    {item.calls !== null && item.calls !== undefined ? item.calls : '—'}
                  </td>
                  <td className="px-4 py-2 text-right text-slate-300 font-bold">
                    {item.transactions !== null && item.transactions !== undefined ? item.transactions : '—'}
                  </td>
                </tr>
              ))}
              {anomalies.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-4 text-center text-textMuted">
                    No active anomaly flags registered.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

