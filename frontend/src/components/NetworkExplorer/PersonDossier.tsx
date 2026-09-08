import React from 'react';
import { Shield, Share2, Activity, AlertCircle, X } from 'lucide-react';
import { PersonDetail } from '../../types';

interface PersonDossierProps {
  person: PersonDetail | null;
  onClose?: () => void;
}

export const PersonDossier: React.FC<PersonDossierProps> = ({ person, onClose }) => {
  if (!person) return null;

  const roleBadgeStyle =
    person.role === 'Kingpin'
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : person.role === 'Intermediary'
      ? 'bg-teal-500/20 text-teal-300 border-teal-500/40'
      : 'bg-blue-500/20 text-blue-300 border-blue-500/40';

  return (
    <div className="bg-surface border border-borderDark rounded-lg p-4 mt-3">
      <div className="flex items-center justify-between pb-3 border-b border-borderDark mb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded bg-slate-800 border border-borderDark text-amberAccent">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold font-mono text-white">{person.name}</h3>
            <span className={`inline-block mt-0.5 px-2 py-0.5 rounded text-[11px] font-mono border ${roleBadgeStyle}`}>
              {person.role}
            </span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 rounded text-textMuted hover:text-white hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3 font-mono">
        <div className="bg-background/80 border border-borderDark p-2.5 rounded">
          <span className="text-[10px] text-textMuted uppercase block">Influence (PageRank)</span>
          <span className="text-sm font-bold text-amberAccent">
            {person.influence !== null && person.influence !== undefined ? person.influence.toFixed(3) : '—'}
          </span>
        </div>

        <div className="bg-background/80 border border-borderDark p-2.5 rounded">
          <span className="text-[10px] text-textMuted uppercase block">Bridge Score</span>
          <span className="text-sm font-bold text-tealAccent">
            {person.bridge_score !== null && person.bridge_score !== undefined ? person.bridge_score.toFixed(2) : '—'}
          </span>
        </div>

        <div className="bg-background/80 border border-borderDark p-2.5 rounded">
          <span className="text-[10px] text-textMuted uppercase block">Operational Cell</span>
          <span className="text-sm font-bold text-slate-200">
            {person.community !== null && person.community !== undefined ? `Cell #${person.community}` : '—'}
          </span>
        </div>

        <div className="bg-background/80 border border-borderDark p-2.5 rounded">
          <span className="text-[10px] text-textMuted uppercase block">Direct Links</span>
          <span className="text-sm font-bold text-slate-200">{person.connections_count}</span>
        </div>
      </div>

      {/* Active Flag Alert if flagged */}
      {person.flag && (
        <div className="flex items-start gap-2 bg-alertRed/10 border border-alertRed/30 p-2.5 rounded mb-3 text-xs font-mono text-alertRed">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold uppercase tracking-wider block text-[10px]">Surveillance Flag:</span>
            <span>{person.flag}</span>
          </div>
        </div>
      )}

      {/* Connected Entities */}
      {person.connected_entities && person.connected_entities.length > 0 && (
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-textMuted block mb-1.5 flex items-center gap-1">
            <Share2 className="w-3 h-3" /> Fused Network Associations ({person.connected_entities.length})
          </span>
          <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto pr-1">
            {person.connected_entities.map((conn, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 bg-background border border-borderDark px-2 py-1 rounded text-xs font-mono text-slate-300"
              >
                <span className="text-slate-400 font-semibold">{conn.entity}</span>
                <span className="text-[10px] text-tealAccent/80 uppercase">({conn.relationship})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

