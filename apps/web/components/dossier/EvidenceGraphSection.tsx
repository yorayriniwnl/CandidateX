'use client';

import dynamic from 'next/dynamic';
import { useMemo, useState } from 'react';
import type { CEGGraph, CEGNode, CapabilityKey } from '../../types/cci';
import styles from './evidence-graph.module.css';

const LazyEvidenceGraph3D = dynamic(
  () => import('./EvidenceGraph3D').then(module => module.EvidenceGraph3D),
  { ssr: false, loading: () => <div className={styles.loading} role="status">Preparing the 3D evidence graph…</div> },
);

const PAGE_SIZE = 48;

function readableType(value: string) {
  return value.replaceAll('_', ' ').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
}

function nodeSummary(node: CEGNode) {
  const details = [node.properties.source_locator, node.properties.artifact_path, node.properties.immutable_revision]
    .filter((value): value is string => typeof value === 'string' && value.length > 0);
  return `${readableType(node.type)} node ${node.label}${details.length ? `; ${details.join('; ')}` : ''}`;
}

function safeValue(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value == null) return 'Not returned';
  try { return JSON.stringify(value); } catch { return 'Details unavailable'; }
}

export function EvidenceGraphSection({ graph, onSelectCapability, onSelectEvidence }: {
  graph: CEGGraph;
  onSelectCapability: (capability: CapabilityKey) => void;
  onSelectEvidence: (evidenceId: string) => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const [query, setQuery] = useState('');
  const [visibleLimit, setVisibleLimit] = useState(PAGE_SIZE);
  const [selectedTextNode, setSelectedTextNode] = useState<CEGNode | null>(null);
  const nodeById = useMemo(() => new Map(graph.nodes.map(node => [node.id, node])), [graph.nodes]);
  const filteredNodes = useMemo(() => {
    const search = query.trim().toLowerCase();
    return graph.nodes.filter(node => !search ||
      `${node.label} ${node.type} ${node.id} ${JSON.stringify(node.properties)}`.toLowerCase().includes(search));
  }, [graph.nodes, query]);
  const visibleNodes = filteredNodes.slice(0, visibleLimit);
  const visibleIds = new Set(visibleNodes.map(node => node.id));
  const visibleEdges = graph.edges.filter(edge => visibleIds.has(edge.source) && visibleIds.has(edge.target));

  function selectNode(node: CEGNode) {
    const type = node.type.toLowerCase().replaceAll('_', '').replaceAll(' ', '');
    if (type === 'evidence' || typeof node.properties.evidence_id === 'string') {
      const evidenceId = typeof node.properties.evidence_id === 'string' ? node.properties.evidence_id : node.id;
      onSelectEvidence(evidenceId);
      return;
    }
    if (type === 'capability' && typeof node.properties.capability_key === 'string') {
      onSelectCapability(node.properties.capability_key as CapabilityKey);
    }
  }

  return (
    <section id="evidence-graph" className={styles.section} aria-labelledby="evidence-graph-title">
      <header className={styles.sectionHeader}>
        <div>
          <p className={styles.eyebrow}>07 / PROVENANCE FIELD</p>
          <h2 id="evidence-graph-title">Candidate evidence graph</h2>
          <p className={styles.lede}>Explore the nodes and relationships returned for this analysis run. A connection records provenance; it does not certify a claim.</p>
        </div>
        <p className={styles.count} aria-label={`${graph.nodes.length} graph nodes and ${graph.edges.length} graph relationships`}>
          <strong>{graph.nodes.length}</strong> nodes <span aria-hidden="true">·</span> <strong>{graph.edges.length}</strong> relationships
        </p>
      </header>

      {graph.nodes.length === 0 ? (
        <p className={styles.empty}>No graph nodes were returned for this run.</p>
      ) : (
        <>
          <div className={styles.graphIntro}>
            <div className={styles.legendStack}>
              <div className={styles.legend} role="group" aria-label="Graph node semantics">
                <span><i className={styles.legendCandidate} />Candidate</span>
                <span><i className={styles.legendSource} />Source</span>
                <span><i className={styles.legendEvidence} />Supporting evidence</span>
                <span><i className={styles.legendConflict} />Conflicting evidence</span>
                <span><i className={styles.legendUnknown} />Unknown capability</span>
                <span><i className={styles.legendRole} />Role requirement</span>
                <span><i className={styles.legendNeutral} />Other graph node</span>
              </div>
              <div className={styles.legend} role="group" aria-label="Graph relationship semantics">
                <span><i className={`${styles.legendLine} ${styles.legendLineSupport}`} />Support</span>
                <span><i className={`${styles.legendLine} ${styles.legendLineConflict}`} />Contradiction</span>
                <span><i className={`${styles.legendLine} ${styles.legendLineQuestion}`} />Interview question</span>
                <span><i className={`${styles.legendLine} ${styles.legendLineOther}`} />Other relationship</span>
              </div>
            </div>
            {!loaded && <button type="button" className={styles.loadButton} onClick={() => setLoaded(true)}>
              <span aria-hidden="true">↗</span> Load 3D evidence graph
            </button>}
            {loaded && <p className={styles.controlsHint}>Drag to rotate · scroll to zoom · hover or select a node to reveal its label and returned details.</p>}
          </div>

          {loaded && <LazyEvidenceGraph3D graph={graph} onSelectNode={selectNode} />}

          <details id="evidence-graph-text-alternative" className={styles.textEquivalent}>
            <summary>Text equivalent · nodes and relationships</summary>
            <label className={styles.searchLabel} htmlFor="graph-node-search">Find a node</label>
            <input
              id="graph-node-search"
              className={styles.search}
              type="search"
              value={query}
              placeholder="Search labels, IDs, source, or path…"
              onChange={event => { setQuery(event.currentTarget.value); setVisibleLimit(PAGE_SIZE); setSelectedTextNode(null); }}
            />
            <div className={styles.alternativeColumns}>
              <div>
                <h3>Nodes · {filteredNodes.length} returned</h3>
                <ul className={styles.nodeList}>
                  {visibleNodes.map(node => <li key={node.id}>
                    <button type="button" aria-label={`Inspect ${nodeSummary(node)}`} onClick={() => { setSelectedTextNode(node); selectNode(node); }}>
                      <span>{readableType(node.type)}</span><strong>{node.label}</strong><code>{node.id}</code>
                    </button>
                  </li>)}
                </ul>
                {filteredNodes.length > visibleNodes.length && <button className={styles.moreButton} type="button" onClick={() => setVisibleLimit(limit => Math.min(filteredNodes.length, limit + PAGE_SIZE))}>
                  Show {Math.min(PAGE_SIZE, filteredNodes.length - visibleNodes.length)} more nodes
                </button>}
              </div>
              <div>
                <h3>Relationships · {graph.edges.length} returned</h3>
                <ul className={styles.edgeList}>
                  {visibleEdges.slice(0, PAGE_SIZE).map(edge => <li key={edge.id}>
                    <code>{edge.type}</code>
                    <span>{nodeById.get(edge.source)?.label ?? edge.source}</span>
                    <b aria-hidden="true">→</b>
                    <span>{nodeById.get(edge.target)?.label ?? edge.target}</span>
                  </li>)}
                </ul>
                {visibleEdges.length > PAGE_SIZE && <p className={styles.note}>Narrow the node search to inspect more relationships in this text view.</p>}
              </div>
            </div>
            {selectedTextNode && <aside className={styles.nodeInspector} aria-label="Selected text graph node details">
              <div className={styles.nodeInspectorHeading}>
                <span>{readableType(selectedTextNode.type)}</span>
                <h3>{selectedTextNode.label}</h3>
                <code>{selectedTextNode.id}</code>
              </div>
              {Object.keys(selectedTextNode.properties).length > 0 ? <dl>
                {Object.entries(selectedTextNode.properties).slice(0, 8).map(([key, value]) => <div key={key}>
                  <dt>{readableType(key)}</dt><dd>{safeValue(value)}</dd>
                </div>)}
              </dl> : <p className={styles.note}>No properties were returned for this node.</p>}
            </aside>}
          </details>
        </>
      )}
    </section>
  );
}
