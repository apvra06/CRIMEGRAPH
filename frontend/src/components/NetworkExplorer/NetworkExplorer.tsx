import React, { useState, useEffect } from 'react';
import { Filter, Calendar, Compass, GitMerge, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../../services/api';
import { GraphNode, GraphEdge, PersonDetail } from '../../types';
import { GraphCanvas } from './GraphCanvas';
import { GraphLegend } from './GraphLegend';
import { PersonDossier } from './PersonDossier';

export const NetworkExplorer: React.FC = () => {
  // Filter States
  const [viewMode, setViewMode] = useState<string>('Whole network');
  const [colorBy, setColorBy] = useState<string>('Entity type');
  const [layout, setLayout] = useState<'Force-directed' | 'Hierarchical (by role)'>('Force-directed');
  const [peopleOnly, setPeopleOnly] = useState<boolean>(false);

  // Dropdown options
  const [people, setPeople] = useState<string[]>([]);
  const [communities, setCommunities] = useState<number[]>([]);
  const [dateRange, setDateRange] = useState<{ start_date: string | null; end_date: string | null }>({
    start_date: null,
    end_date: null,
  });

  // Selected filters
  const [selectedPerson, setSelectedPerson] = useState<string>('');
  const [selectedCommunity, setSelectedCommunity] = useState<number | undefined>(undefined);
  const [useTimeline, setUseTimeline] = useState<boolean>(false);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Shortest Path States
  const [pathFrom, setPathFrom] = useState<string>('');
  const [pathTo, setPathTo] = useState<string>('');
  const [pathMessage, setPathMessage] = useState<string | null>(null);

  // Graph Data
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Inspected suspect detail
  const [inspectedPerson, setInspectedPerson] = useState<PersonDetail | null>(null);

  // Initial load of dropdown lists
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [peopleList, commsList, dates] = await Promise.all([
          api.getPeople(),
          api.getCommunities(),
          api.getDateRange(),
        ]);
        setPeople(peopleList);
        if (peopleList.length > 0) {
          setSelectedPerson(peopleList[0]);
          setPathFrom(peopleList[0]);
          if (peopleList.length > 1) {
            setPathTo(peopleList[1]);
          }
        }
        setCommunities(commsList);
        if (commsList.length > 0) {
          setSelectedCommunity(commsList[0]);
        }
        setDateRange(dates);
        if (dates.start_date && dates.end_date) {
          setStartDate(dates.start_date);
          setEndDate(dates.end_date);
        }
      } catch (err) {
        console.error('Error loading metadata:', err);
      }
    };
    fetchMetadata();
  }, []);

  // Fetch graph data whenever view parameters change
  useEffect(() => {
    if (viewMode === 'Path between two people') {
      return; // Handled by explicit button click
    }

    const fetchGraph = async () => {
      setLoading(true);
      try {
        const data = await api.getGraphData({
          view_mode: viewMode,
          person: viewMode === 'Specific person' ? selectedPerson : undefined,
          community: viewMode === 'Specific community' ? selectedCommunity : undefined,
          start_date: useTimeline ? startDate : undefined,
          end_date: useTimeline ? endDate : undefined,
          people_only: peopleOnly || layout === 'Hierarchical (by role)',
          color_by: colorBy,
        });
        setNodes(data.nodes);
        setEdges(data.edges);
      } catch (err) {
        console.error('Failed to fetch graph data:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
  }, [viewMode, selectedPerson, selectedCommunity, useTimeline, startDate, endDate, peopleOnly, colorBy, layout]);

  // Handle Find Shortest Path
  const handleFindPath = async () => {
    if (!pathFrom || !pathTo) return;
    setLoading(true);
    setPathMessage(null);
    try {
      const res = await api.findShortestPath(pathFrom, pathTo);
      if (res.found) {
        setNodes(res.path_nodes);
        setEdges(res.path_edges);
        setPathMessage(res.message || `Path found (${res.path_nodes.length} nodes)`);
      } else {
        setNodes([]);
        setEdges([]);
        setPathMessage(res.message || 'No connection path found between these two people.');
      }
    } catch (err) {
      setPathMessage('Error querying shortest path.');
    } finally {
      setLoading(false);
    }
  };

  // Node selection handler for dossier display
  const handleNodeClick = async (node: GraphNode | null) => {
    if (!node) {
      setInspectedPerson(null);
      return;
    }
    if (node.type === 'Person') {
      try {
        const detail = await api.getPersonDetail(node.label);
        setInspectedPerson(detail);
      } catch (err) {
        setInspectedPerson(null);
      }
    } else {
      setInspectedPerson(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Control Panel */}
      <div className="bg-surface border border-borderDark rounded-lg p-4 space-y-4">
        {/* Mode & Color Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pb-3 border-b border-borderDark/80">
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-textMuted block mb-1.5 flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-amberAccent" /> View Mode
            </label>
            <div className="flex flex-wrap gap-1.5">
              {['Whole network', 'Specific person', 'Specific community', 'Path between two people'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                    viewMode === mode
                      ? 'bg-amberAccent/20 border-amberAccent text-amberAccent font-semibold'
                      : 'bg-background border-borderDark text-slate-300 hover:border-slate-600'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-textMuted block mb-1.5">
              Color Palette By
            </label>
            <div className="flex gap-2">
              {['Entity type', 'Community'].map((c) => (
                <button
                  key={c}
                  onClick={() => setColorBy(c)}
                  className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${
                    colorBy === c
                      ? 'bg-tealAccent/20 border-tealAccent text-tealAccent font-semibold'
                      : 'bg-background border-borderDark text-slate-300 hover:border-slate-600'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-textMuted block mb-1.5">
              Graph Layout
            </label>
            <div className="flex gap-2">
              {['Force-directed', 'Hierarchical (by role)'].map((l) => (
                <button
                  key={l}
                  onClick={() => setLayout(l as any)}
                  className={`px-2.5 py-1 rounded text-xs font-mono border transition-colors ${
                    layout === l
                      ? 'bg-amberAccent/20 border-amberAccent text-amberAccent font-semibold'
                      : 'bg-background border-borderDark text-slate-300 hover:border-slate-600'
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center pt-5">
            <label className="inline-flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={peopleOnly || layout === 'Hierarchical (by role)'}
                onChange={(e) => setPeopleOnly(e.target.checked)}
                className="w-4 h-4 rounded bg-background border-borderDark text-amberAccent focus:ring-amberAccent"
              />
              <span>People Only (Hide Non-Person Nodes)</span>
            </label>
          </div>
        </div>

        {/* Dynamic Context Filters */}
        <div className="flex flex-wrap items-center gap-4">
          {viewMode === 'Specific person' && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-textMuted">Select Suspect:</span>
              <select
                value={selectedPerson}
                onChange={(e) => setSelectedPerson(e.target.value)}
                className="bg-background border border-borderDark text-slate-200 text-xs font-mono rounded px-3 py-1.5 focus:border-amberAccent outline-none"
              >
                {people.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )}

          {viewMode === 'Specific community' && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-textMuted">Select Cell / Community:</span>
              <select
                value={selectedCommunity}
                onChange={(e) => setSelectedCommunity(Number(e.target.value))}
                className="bg-background border border-borderDark text-slate-200 text-xs font-mono rounded px-3 py-1.5 focus:border-amberAccent outline-none"
              >
                {communities.map((c) => (
                  <option key={c} value={c}>
                    Community #{c}
                  </option>
                ))}
              </select>
            </div>
          )}

          {viewMode === 'Path between two people' && (
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-textMuted">From:</span>
                <select
                  value={pathFrom}
                  onChange={(e) => setPathFrom(e.target.value)}
                  className="bg-background border border-borderDark text-slate-200 text-xs font-mono rounded px-3 py-1.5 focus:border-amberAccent outline-none"
                >
                  {people.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-textMuted">To:</span>
                <select
                  value={pathTo}
                  onChange={(e) => setPathTo(e.target.value)}
                  className="bg-background border border-borderDark text-slate-200 text-xs font-mono rounded px-3 py-1.5 focus:border-amberAccent outline-none"
                >
                  {people
                    .filter((p) => p !== pathFrom)
                    .map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                </select>
              </div>

              <button
                onClick={handleFindPath}
                disabled={loading}
                className="inline-flex items-center gap-1.5 bg-amberAccent/20 hover:bg-amberAccent/30 text-amberAccent border border-amberAccent px-3 py-1.5 rounded text-xs font-mono font-semibold transition"
              >
                <GitMerge className="w-3.5 h-3.5" /> Find Connection Path
              </button>
            </div>
          )}

          {/* Timeline Filter Toggle */}
          <div className="flex items-center gap-3 ml-auto">
            <label className="inline-flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={useTimeline}
                onChange={(e) => setUseTimeline(e.target.checked)}
                className="w-4 h-4 rounded bg-background border-borderDark text-tealAccent focus:ring-tealAccent"
              />
              <Calendar className="w-3.5 h-3.5 text-tealAccent" />
              <span>Timeline Window Filter</span>
            </label>

            {useTimeline && dateRange.start_date && (
              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-background border border-borderDark px-2 py-1 rounded text-slate-200"
                />
                <span>to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-background border border-borderDark px-2 py-1 rounded text-slate-200"
                />
              </div>
            )}
          </div>
        </div>

        {/* Path Alert Message */}
        {pathMessage && (
          <div className="flex items-center gap-2 text-xs font-mono p-2 rounded bg-slate-900 border border-borderDark text-amberAccent">
            <AlertCircle className="w-4 h-4 text-amberAccent" />
            <span>{pathMessage}</span>
          </div>
        )}
      </div>

      {/* Graph Visualizer Canvas & Legend */}
      <div className="space-y-2">
        <GraphLegend colorBy={colorBy} />
        <div className="relative">
          {loading && (
            <div className="absolute inset-0 bg-background/60 backdrop-blur-[1px] z-20 flex items-center justify-center">
              <div className="flex items-center gap-2 px-4 py-2 bg-surface border border-borderDark rounded text-amberAccent font-mono text-xs shadow-xl">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Computing graph topology...</span>
              </div>
            </div>
          )}
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            layout={layout}
            onNodeClick={handleNodeClick}
            height={620}
          />
        </div>
      </div>

      {/* Selected Suspect Dossier Card */}
      {inspectedPerson && (
        <PersonDossier person={inspectedPerson} onClose={() => setInspectedPerson(null)} />
      )}
    </div>
  );
};

