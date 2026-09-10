import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import { Maximize2, ZoomIn, ZoomOut, RefreshCcw } from 'lucide-react';
import { GraphNode, GraphEdge } from '../../types';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  layout: 'Force-directed' | 'Hierarchical (by role)';
  onNodeClick: (node: GraphNode | null) => void;
  height?: number;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  layout,
  onNodeClick,
  height = 620,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Convert nodes to vis dataset format
    const visNodes = new DataSet(
      nodes.map((n) => ({
        id: n.id,
        label: n.label,
        title: n.title,
        shape: n.style.shape,
        color: {
          background: n.style.color,
          border: n.style.color,
          highlight: {
            background: '#FFFFFF',
            border: n.style.color,
          },
        },
        size: n.style.size,
        borderWidth: n.style.borderWidth || 1,
        level: n.level !== null && n.level !== undefined ? n.level : undefined,
        font: {
          color: '#EEEEEE',
          size: 13,
          face: 'IBM Plex Mono, monospace',
        },
      }))
    );

    // Convert edges to vis dataset format
    const visEdges = new DataSet(
      edges.map((e) => ({
        id: e.id,
        from: e.from,
        to: e.to,
        title: e.title,
        color: {
          color: e.color || '#555555',
          highlight: '#C99A3C',
          hover: '#C99A3C',
        },
        width: e.width || 1,
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.2,
        },
      }))
    );

    // Setup layout options
    let options: any = {
      interaction: {
        hover: true,
        navigationButtons: false,
        keyboard: true,
        tooltipDelay: 100,
      },
    };

    if (layout === 'Hierarchical (by role)') {
      options = {
        ...options,
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            levelSeparation: 150,
            nodeSpacing: 130,
          },
        },
        physics: {
          hierarchicalRepulsion: {
            nodeDistance: 130,
          },
          solver: 'hierarchicalRepulsion',
          stabilization: {
            enabled: true,
            iterations: 200,
          },
        },
      };
    } else {
      options = {
        ...options,
        physics: {
          barnesHut: {
            gravitationalConstant: -4000,
            centralGravity: 0.35,
            springLength: 110,
            springConstant: 0.045,
            damping: 0.15,
          },
          solver: 'barnesHut',
          stabilization: {
            enabled: true,
            iterations: 200,
          },
        },
      };
    }

    const data = { nodes: visNodes, edges: visEdges };
    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // Handle stabilization fit
    network.once('stabilizationIterationsDone', () => {
      network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    });

    // Handle node selection
    network.on('click', (params) => {
      if (params.nodes && params.nodes.length > 0) {
        const selectedId = String(params.nodes[0]);
        const matched = nodes.find((n) => String(n.id) === selectedId || n.label === selectedId);
        onNodeClick(matched || null);
      } else {
        onNodeClick(null);
      }
    });

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, layout]);

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale() * 1.25;
      networkRef.current.moveTo({ scale, animation: true });
    }
  };

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale() / 1.25;
      networkRef.current.moveTo({ scale, animation: true });
    }
  };

  const handleFit = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } });
    }
  };

  return (
    <div className="relative w-full rounded border border-borderDark bg-[#0E1117] overflow-hidden">
      <div
        ref={containerRef}
        style={{ height: `${height}px`, width: '100%' }}
        className="vis-network"
      />

      {/* Canvas overlay buttons */}
      <div className="absolute top-3 right-3 flex flex-col gap-1.5 bg-surface/90 border border-borderDark rounded p-1 shadow-lg z-10">
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFit}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
          title="Fit Network"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0E1117]/80 text-textMuted font-mono text-sm">
          No network data matches your current filter parameters.
        </div>
      )}
    </div>
  );
};

