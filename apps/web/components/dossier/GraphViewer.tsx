'use client';

import React, { useState, useMemo } from 'react';
import {
  Code,
  FileText,
  Filter,
  GitBranch,
  Layers,
  Network,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Info,
  Shield,
  ExternalLink,
} from 'lucide-react';
import { CEGGraph, CEGNode, CEGEdge, CapabilityKey } from '../../types/cci';

const NODE_TYPE_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; icon: React.ComponentType<{ className?: string }> }
> = {
  source: {
    label: 'Source',
    color: 'text-sky-400',
    bg: 'fill-sky-950/80',
    border: 'stroke-sky-500',
    icon: GitBranch,
  },
  artifact: {
    label: 'Artifact',
    color: 'text-amber-400',
    bg: 'fill-amber-950/80',
    border: 'stroke-amber-500',
    icon: FileText,
  },
  evidence: {
    label: 'Evidence',
    color: 'text-emerald-400',
    bg: 'fill-emerald-950/80',
    border: 'stroke-emerald-500',
    icon: Shield,
  },
  capability: {
    label: 'Capability',
    color: 'text-indigo-400',
    bg: 'fill-indigo-950/80',
    border: 'stroke-indigo-500',
    icon: Layers,
  },
  claim: {
    label: 'Self-Claim',
    color: 'text-purple-400',
    bg: 'fill-purple-950/80',
    border: 'stroke-purple-500',
    icon: Code,
  },
};

export const GraphViewer: React.FC<{
  graph: CEGGraph;
  selectedCapability?: CapabilityKey | null;
  onSelectCapability?: (key: CapabilityKey) => void;
}> = ({ graph, selectedCapability, onSelectCapability }) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Partition nodes into layered columns
  // Column 0: Sources & Claims
  // Column 1: Artifacts
  // Column 2: Evidence
  // Column 3: Capabilities
  const { nodePositions, visibleNodes, visibleEdges } = useMemo(() => {
    const nodes = graph.nodes.filter((n) => {
      if (typeFilter !== 'all' && n.type !== typeFilter) return false;
      if (searchQuery && !n.label.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      if (selectedCapability && n.properties?.capability && n.properties.capability !== selectedCapability) {
        return false;
      }
      return true;
    });

    const nodeSet = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter((e) => nodeSet.has(e.source) && nodeSet.has(e.target));

    const layers: Record<string, CEGNode[]> = {
      source: [],
      claim: [],
      artifact: [],
      evidence: [],
      capability: [],
    };

    nodes.forEach((n) => {
      const t = n.type.toLowerCase();
      if (layers[t]) {
        layers[t].push(n);
      } else {
        layers.source.push(n);
      }
    });

    // Compute coordinate positions in SVG
    const colX: Record<string, number> = {
      source: 80,
      claim: 80,
      artifact: 320,
      evidence: 580,
      capability: 840,
    };

    const positions: Record<string, { x: number; y: number }> = {};
    const colYCounter: Record<string, number> = {
      source: 60,
      claim: 60,
      artifact: 60,
      evidence: 60,
      capability: 60,
    };

    nodes.forEach((n) => {
      const t = n.type.toLowerCase();
      const x = colX[t] || 80;
      const y = colYCounter[t];
      colYCounter[t] += 70;
      positions[n.id] = { x, y };
    });

    return { nodePositions: positions, visibleNodes: nodes, visibleEdges: edges };
  }, [graph, typeFilter, searchQuery, selectedCapability]);

  const selectedNode = useMemo(() => {
    return graph.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [graph, selectedNodeId]);

  // Backward provenance trace for selected node
  const activeAncestors = useMemo(() => {
    if (!selectedNodeId) return new Set<string>();
    const ancestors = new Set<string>([selectedNodeId]);
    const queue = [selectedNodeId];

    while (queue.length > 0) {
      const current = queue.shift()!;
      // Find all edges where target === current (backward trace)
      graph.edges.forEach((e) => {
        if (e.target === current && !ancestors.has(e.source)) {
          ancestors.add(e.source);
          queue.push(e.source);
        }
      });
    }
    return ancestors;
  }, [graph, selectedNodeId]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Network className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">Candidate Evidence Graph (CEG)</h2>
            <p className="text-xs text-slate-400">
              Interactive backward provenance tracing from capability estimates to raw repository ASTs & commits
            </p>
          </div>
        </div>

        {/* Graph Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search graph..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-36"
            />
          </div>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Node Types</option>
            <option value="source">Sources</option>
            <option value="claim">Self-Claims</option>
            <option value="artifact">Artifacts</option>
            <option value="evidence">Evidence</option>
            <option value="capability">Capabilities</option>
          </select>

          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setSelectedNodeId(null);
              }}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Graph Canvas & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* SVG Diagram Canvas */}
        <div className="lg:col-span-3 bg-slate-950 border border-slate-800 rounded-xl overflow-auto h-[480px] relative">
          <div
            className="min-w-[960px] min-h-[460px] p-4 transition-transform duration-150 origin-top-left"
            style={{ transform: `scale(${zoom})` }}
          >
            <svg width="960" height="460" className="select-none">
              <defs>
                <marker
                  id="arrow"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#64748b" />
                </marker>
                <marker
                  id="arrow-active"
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#6366f1" />
                </marker>
              </defs>

              {/* Column Guides */}
              <g opacity="0.3" className="text-[10px] font-mono fill-slate-500">
                <text x="80" y="24" textAnchor="middle">SOURCES &amp; CLAIMS</text>
                <text x="320" y="24" textAnchor="middle">PARSED ARTIFACTS</text>
                <text x="580" y="24" textAnchor="middle">EVIDENCE RECORDS</text>
                <text x="840" y="24" textAnchor="middle">CAPABILITIES</text>
              </g>

              {/* Edges */}
              {visibleEdges.map((edge) => {
                const src = nodePositions[edge.source];
                const dst = nodePositions[edge.target];
                if (!src || !dst) return null;

                const isEdgeActive =
                  activeAncestors.has(edge.source) && activeAncestors.has(edge.target);

                const cX1 = src.x + (dst.x - src.x) * 0.5;
                const cX2 = src.x + (dst.x - src.x) * 0.5;
                const d = `M ${src.x + 40} ${src.y} C ${cX1} ${src.y}, ${cX2} ${dst.y}, ${dst.x - 40} ${dst.y}`;

                return (
                  <path
                    key={edge.id}
                    d={d}
                    fill="none"
                    stroke={isEdgeActive ? '#6366f1' : '#334155'}
                    strokeWidth={isEdgeActive ? 2.5 : 1.2}
                    strokeDasharray={isEdgeActive ? undefined : '3,3'}
                    markerEnd={isEdgeActive ? 'url(#arrow-active)' : 'url(#arrow)'}
                    className="transition-colors duration-200"
                  />
                );
              })}

              {/* Nodes */}
              {visibleNodes.map((node) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;

                const isSelected = selectedNodeId === node.id;
                const isAncestor = activeAncestors.has(node.id);
                const cfg = NODE_TYPE_CONFIG[node.type.toLowerCase()] || NODE_TYPE_CONFIG.artifact;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={() => {
                      setSelectedNodeId(node.id);
                      if (node.properties?.capability && onSelectCapability) {
                        onSelectCapability(node.properties.capability);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <rect
                      x="-60"
                      y="-20"
                      width="120"
                      height="40"
                      rx="8"
                      className={`${cfg.bg} ${cfg.border} transition-all duration-200 ${
                        isSelected
                          ? 'stroke-2 stroke-indigo-400 filter drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]'
                          : isAncestor
                          ? 'stroke-2 stroke-indigo-500'
                          : 'stroke-1'
                      }`}
                    />
                    <text
                      x="0"
                      y="4"
                      textAnchor="middle"
                      className="text-[11px] font-medium fill-slate-200 pointer-events-none select-none"
                    >
                      {node.label.length > 14 ? node.label.slice(0, 13) + '…' : node.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Node Details Inspection Panel */}
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5 mb-3">
              <Info className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                Provenance Inspector
              </h3>
            </div>

            {selectedNode ? (
              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                    Type / Node ID
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-indigo-300 rounded font-mono text-[11px]">
                      {selectedNode.type}
                    </span>
                    <span className="text-slate-400 font-mono text-[11px] truncate">
                      {selectedNode.id}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                    Label
                  </span>
                  <p className="text-slate-100 font-medium mt-0.5">{selectedNode.label}</p>
                </div>

                {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 && (
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono mb-1">
                      Properties &amp; Calibration
                    </span>
                    <div className="bg-slate-900 border border-slate-800 rounded p-2 max-h-48 overflow-y-auto space-y-1 font-mono text-[11px]">
                      {Object.entries(selectedNode.properties).map(([k, v]) => (
                        <div key={k} className="flex justify-between gap-2">
                          <span className="text-slate-400 truncate">{k}:</span>
                          <span className="text-slate-200 font-semibold truncate">
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                Click on any node in the evidence graph to inspect its backward provenance chain.
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-slate-800/80 text-[10px] text-slate-500">
            CEG provides formal auditability from top-level RCI to concrete file lines.
          </div>
        </div>
      </div>
    </div>
  );
};
