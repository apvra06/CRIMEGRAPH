import React, { useState } from 'react';
import { Send, Sparkles, BookOpen, UserCheck, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { AskQuestionResponse } from '../../types';

export const AskQuestion: React.FC = () => {
  const [query, setQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<AskQuestionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sampleQueries = [
    'Who are the operational kingpins and what cells do they direct?',
    'Which intermediaries maintain the highest bridge scores between cells?',
    'What suspicious financial structuring or CDR call spikes have been flagged?',
    'Give me an operational overview of the highest threat suspects in Case NCRB-2026-0847.',
  ];

  const handleSearch = async (textToSearch?: string) => {
    const q = textToSearch || query;
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.askQuestion(q);
      setResult(res);
    } catch (err) {
      setError('Unable to retrieve AI intelligence analysis. Check backend logs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Intro Header */}
      <div className="bg-surface border border-borderDark rounded-lg p-5 border-l-4 border-l-amberAccent">
        <div className="flex items-center gap-2.5 text-amberAccent mb-2 font-mono text-sm font-semibold">
          <Sparkles className="w-4 h-4" />
          <span>Gemini Intelligence Analyst Assistant</span>
        </div>
        <p className="text-xs text-textMuted leading-relaxed">
          Ask conversational queries against the fused crime knowledge graph. The AI engine synthesizes FIR
          narratives, call detail records (CDR), and financial ledger trails to surface hidden relationships.
        </p>
      </div>

      {/* Query Input Box */}
      <div className="bg-surface border border-borderDark rounded-lg p-4 space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="E.g., Which suspects act as conduits for money laundering between cell leaders?"
            className="flex-1 bg-background border border-borderDark text-sm text-slate-200 rounded px-4 py-2.5 focus:border-amberAccent outline-none font-mono placeholder:text-textMuted/60"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 bg-amberAccent/20 hover:bg-amberAccent/30 text-amberAccent border border-amberAccent font-mono text-xs font-semibold rounded inline-flex items-center gap-2 transition disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>Analyze</span>
          </button>
        </div>

        {/* Suggested Queries Chips */}
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-textMuted block mb-1.5">
            Suggested Intelligence Queries:
          </span>
          <div className="flex flex-wrap gap-2">
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(sq);
                  handleSearch(sq);
                }}
                className="text-left text-xs font-mono bg-background/80 hover:bg-background border border-borderDark hover:border-slate-600 text-slate-300 px-2.5 py-1.5 rounded transition"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-alertRed/10 border border-alertRed/30 text-alertRed text-xs font-mono rounded">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* AI Intelligence Result Card */}
      {result && (
        <div className="bg-surface border border-borderDark rounded-lg p-6 space-y-5 animate-in fade-in duration-300">
          <div className="flex items-center justify-between pb-3 border-b border-borderDark">
            <span className="text-xs font-mono text-amberAccent uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Intelligence Assessment
            </span>
            <span className="text-[10px] font-mono text-textMuted">Confidence: High</span>
          </div>

          <div className="text-sm text-slate-200 leading-relaxed font-sans whitespace-pre-wrap">
            {result.answer}
          </div>

          {/* Related Suspects */}
          {result.related_entities && result.related_entities.length > 0 && (
            <div className="pt-3 border-t border-borderDark/60">
              <span className="text-[10px] font-mono uppercase tracking-wider text-textMuted block mb-2 flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-tealAccent" /> Identified Entities in Scope
              </span>
              <div className="flex flex-wrap gap-1.5">
                {result.related_entities.map((ent, idx) => (
                  <span
                    key={idx}
                    className="bg-background border border-borderDark px-2.5 py-1 rounded text-xs font-mono text-tealAccent font-medium"
                  >
                    {ent}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Citations */}
          {result.citations && result.citations.length > 0 && (
            <div className="pt-3 border-t border-borderDark/60 flex items-center gap-2 text-xs font-mono text-textMuted">
              <BookOpen className="w-3.5 h-3.5 text-amberAccent" />
              <span>Evidence Corroboration:</span>
              <span className="text-slate-400">{result.citations.join(' • ')}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

