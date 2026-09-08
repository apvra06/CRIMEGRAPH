import React from 'react';

interface GraphLegendProps {
  colorBy: string;
}

export const GraphLegend: React.FC<GraphLegendProps> = ({ colorBy }) => {
  const roles = [
    { label: 'Kingpin', glyph: '★', color: '#E5B94E' },
    { label: 'Intermediary', glyph: '◆', color: '#4FB6AC' },
    { label: 'Associate', glyph: '●', color: '#6B93C9' },
  ];

  const entityTypes = [
    { label: 'Location', glyph: '■', color: '#5E8FC9' },
    { label: 'Organization', glyph: '▲', color: '#8C7BC9' },
    { label: 'PhoneNumber', glyph: '▼', color: '#9CC97B' },
    { label: 'Vehicle', glyph: '▢', color: '#C97B9C' },
  ];

  const communities = [
    { label: 'Community 0', color: '#C99A3C' },
    { label: 'Community 1', color: '#4FB6AC' },
    { label: 'Community 2', color: '#8C7BC9' },
    { label: 'Community 3', color: '#9CC97B' },
  ];

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 py-2 px-3 bg-surface/80 border border-borderDark rounded text-xs font-mono text-textMuted">
      <div className="flex items-center gap-3">
        <span className="text-slate-400 font-semibold uppercase text-[10px]">Roles:</span>
        {roles.map((r) => (
          <div key={r.label} className="inline-flex items-center gap-1.5">
            <span style={{ color: r.color }} className="text-sm leading-none font-bold">
              {r.glyph}
            </span>
            <span className="text-slate-300">{r.label}</span>
          </div>
        ))}
      </div>

      <div className="h-3 w-[1px] bg-borderDark hidden sm:block"></div>

      {colorBy === 'Entity type' ? (
        <div className="flex items-center gap-3">
          <span className="text-slate-400 font-semibold uppercase text-[10px]">Entities:</span>
          {entityTypes.map((e) => (
            <div key={e.label} className="inline-flex items-center gap-1.5">
              <span style={{ color: e.color }} className="text-xs leading-none">
                {e.glyph}
              </span>
              <span className="text-slate-300">{e.label}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <span className="text-slate-400 font-semibold uppercase text-[10px]">Communities:</span>
          {communities.map((c) => (
            <div key={c.label} className="inline-flex items-center gap-1.5">
              <span style={{ color: c.color }} className="text-xs">
                ●
              </span>
              <span className="text-slate-300">{c.label}</span>
            </div>
          ))}
        </div>
      )}

      <div className="h-3 w-[1px] bg-borderDark hidden sm:block"></div>

      <div className="inline-flex items-center gap-1.5 text-alertRed">
        <span className="text-sm leading-none font-bold">⚠</span>
        <span className="text-alertRed font-medium">Flagged anomaly</span>
      </div>
    </div>
  );
};

