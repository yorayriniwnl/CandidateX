'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { CEGGraph, CEGNode } from '../../types/cci';
import styles from './evidence-graph.module.css';

const MAX_3D_NODES = 180;
const MAX_3D_EDGES = 420;
const TYPE_ELEVATION: Record<string, number> = {
  candidate: 0, identity: 1.65, source: -1.55, repository: -1.55,
  artifact: 1.45, evidence: -0.35, capability: 1.9, rolerequirement: -1.8,
  analysisrun: 0.25, dossieritem: 0.75,
};
const TYPE_DEPTH: Record<string, number> = {
  candidate: 0, identity: -1.65, source: 1.6, repository: 1.6,
  artifact: 2.35, evidence: -2.05, capability: 0.85, rolerequirement: -1.5,
  analysisrun: 1.9, dossieritem: -1.2,
};
const FALLBACK_LANE_ELEVATION = [0, 0, 0, 0.15, 0, 0.25];
const FALLBACK_LANE_DEPTH = [0, 0, 0, 0.2, 0, 0];

type Tone = 'candidate' | 'source' | 'observed' | 'conflict' | 'unknown' | 'role' | 'neutral';

function normalizedType(value: string) {
  return value.toLowerCase().replace(/[^a-z]/g, '');
}

function laneFor(node: CEGNode) {
  switch (normalizedType(node.type)) {
    case 'candidate':
    case 'identity': return 0;
    case 'source':
    case 'repository': return 1;
    case 'artifact': return 2;
    case 'evidence': return 3;
    case 'capability':
    case 'rolerequirement': return 4;
    case 'analysisrun':
    case 'dossieritem': return 5;
    default: return 3;
  }
}

function toneFor(node: CEGNode): Tone {
  const type = normalizedType(node.type);
  if (type === 'candidate') return 'candidate';
  if (type === 'source') return 'source';
  if (type === 'evidence') return node.properties.is_positive_support === false ? 'conflict' : 'observed';
  if (type === 'capability') return node.properties.is_observed === true ? 'observed' : 'unknown';
  if (type === 'rolerequirement') return 'role';
  return 'neutral';
}

function stableUnit(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
  }
  return (hash >>> 0) / 4294967295;
}

function relationshipColor(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes('contradict')) return '#ff6d7c';
  if (normalized.includes('support')) return '#48e0a0';
  if (normalized.includes('question')) return '#f5c35f';
  return '#a5b4c6';
}

function typeLabel(type: string) {
  return type.replaceAll('_', ' ').replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
}

function propertyValue(value: unknown) {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value == null) return 'Not returned';
  try { return JSON.stringify(value); } catch { return 'Not returned'; }
}

export function EvidenceGraph3D({ graph, onSelectNode }: {
  graph: CEGGraph;
  onSelectNode: (node: CEGNode) => void;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onSelectNodeRef = useRef(onSelectNode);
  const resetViewRef = useRef<(() => void) | null>(null);
  const [activeNode, setActiveNode] = useState<CEGNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<CEGNode | null>(null);
  const [webglUnavailable, setWebglUnavailable] = useState(false);
  onSelectNodeRef.current = onSelectNode;

  useEffect(() => {
    const host = hostRef.current;
    if (!host || graph.nodes.length === 0) return;

    const nodes = graph.nodes.slice(0, MAX_3D_NODES);
    const visibleNodeIds = new Set(nodes.map(node => node.id));
    const edges = graph.edges.filter(edge => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)).slice(0, MAX_3D_EDGES);
    const nodesByLane = new Map<number, CEGNode[]>();
    for (const node of nodes) {
      const lane = laneFor(node);
      nodesByLane.set(lane, [...(nodesByLane.get(lane) ?? []), node]);
    }

    const positions = new Map<string, THREE.Vector3>();
    for (const [lane, laneNodes] of nodesByLane) {
      laneNodes.forEach((node, index) => {
        const verticalSpacing = Math.min(0.82, 8 / Math.max(laneNodes.length, 1));
        const centeredIndex = index - ((laneNodes.length - 1) / 2);
        const normalized = normalizedType(node.type);
        const baseElevation = TYPE_ELEVATION[normalized] ?? FALLBACK_LANE_ELEVATION[lane] ?? 0;
        const baseDepth = TYPE_DEPTH[normalized] ?? FALLBACK_LANE_DEPTH[lane] ?? 0;
        const y = baseElevation + centeredIndex * verticalSpacing + (stableUnit(`${node.id}:y`) - 0.5) * 0.65;
        const z = baseDepth + (stableUnit(`${node.id}:z`) - 0.5) * 1.1;
        positions.set(node.id, new THREE.Vector3(lane * 2.55 - 6.35, y, z));
      });
    }

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'low-power' });
    } catch {
      setWebglUnavailable(true);
      return;
    }

    let frame = 0;
    let visible = true;
    let disposed = false;
    let contextLost = false;
    setWebglUnavailable(false);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(Math.max(host.clientWidth, 320), Math.max(host.clientHeight, 360), false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.domElement.className = styles.canvas;
    renderer.domElement.setAttribute('role', 'img');
    renderer.domElement.setAttribute('aria-label', `3D evidence graph with ${graph.nodes.length} nodes and ${graph.edges.length} relationships`);
    renderer.domElement.setAttribute('aria-describedby', 'evidence-graph-text-alternative');
    renderer.domElement.tabIndex = 0;
    const onContextLost = (event: Event) => {
      event.preventDefault();
      contextLost = true;
      visible = false;
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
      renderer.domElement.setAttribute('aria-hidden', 'true');
      renderer.domElement.tabIndex = -1;
      renderer.domElement.style.visibility = 'hidden';
      setWebglUnavailable(true);
    };
    renderer.domElement.addEventListener('webglcontextlost', onContextLost, false);
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#07090d');
    scene.fog = new THREE.FogExp2('#07090d', 0.013);

    const camera = new THREE.PerspectiveCamera(37, Math.max(host.clientWidth, 320) / Math.max(host.clientHeight, 360), 0.1, 120);
    const bounds = new THREE.Box3().setFromPoints([...positions.values()]);
    const center = bounds.getCenter(new THREE.Vector3());
    const sphere = bounds.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 6);
    const restingPosition = center.clone().add(new THREE.Vector3(radius * 0.95, radius * 0.82, radius * 1.48));
    camera.position.copy(restingPosition);
    camera.lookAt(center);

    const hemisphere = new THREE.HemisphereLight('#dce8ff', '#080a10', 1.6);
    scene.add(hemisphere);
    const keyLight = new THREE.PointLight('#a9a0ff', 48, 46, 1.9);
    keyLight.position.set(-5, 7, 9);
    scene.add(keyLight);
    const evidenceLight = new THREE.PointLight('#30d58a', 25, 34, 2.2);
    evidenceLight.position.set(2, -2, 5);
    scene.add(evidenceLight);

    const controls = new OrbitControls(camera, renderer.domElement);
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    controls.target.copy(center);
    controls.enableDamping = !reduceMotion;
    controls.dampingFactor = 0.075;
    controls.enablePan = false;
    controls.minDistance = Math.max(radius * 0.78, 4.5);
    controls.maxDistance = radius * 4.2;
    controls.minPolarAngle = 0.18;
    controls.maxPolarAngle = Math.PI - 0.18;
    controls.rotateSpeed = 0.62;
    controls.zoomSpeed = 0.78;
    controls.update();

    const materialByTone = new Map<Tone, THREE.MeshStandardMaterial>();
    const colorByTone: Record<Tone, string> = {
      candidate: '#f5f7fb', source: '#9bb8d4', observed: '#48e0a0', conflict: '#ff6d7c',
      unknown: '#9aa9bb', role: '#96a0ff', neutral: '#758396',
    };
    const glowCanvas = document.createElement('canvas');
    glowCanvas.width = 64;
    glowCanvas.height = 64;
    const glowContext = glowCanvas.getContext('2d');
    if (glowContext) {
      const gradient = glowContext.createRadialGradient(32, 32, 0, 32, 32, 32);
      gradient.addColorStop(0, 'rgba(255, 255, 255, 0.56)');
      gradient.addColorStop(0.28, 'rgba(255, 255, 255, 0.22)');
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
      glowContext.fillStyle = gradient;
      glowContext.fillRect(0, 0, 64, 64);
    }
    const glowTexture = new THREE.CanvasTexture(glowCanvas);
    glowTexture.colorSpace = THREE.SRGBColorSpace;
    const glowMaterialByTone = new Map<Tone, THREE.SpriteMaterial>();
    const nodeGeometry = new THREE.SphereGeometry(0.2, 28, 28);
    const nodeMeshes: THREE.Mesh[] = [];
    const nodeLabelMaterials: THREE.SpriteMaterial[] = [];
    const candidateNode = nodes.find(node => normalizedType(node.type) === 'candidate');
    for (const node of nodes) {
      const tone = toneFor(node);
      const type = normalizedType(node.type);
      const position = positions.get(node.id);
      let material = materialByTone.get(tone);
      if (!material) {
        const color = new THREE.Color(colorByTone[tone]);
        material = new THREE.MeshStandardMaterial({
          color,
          emissive: color,
          emissiveIntensity: tone === 'observed' || tone === 'conflict' ? 0.62 : tone === 'candidate' ? 0.4 : 0.32,
          metalness: 0.2,
          roughness: 0.22,
        });
        materialByTone.set(tone, material);
      }
      let glowMaterial = glowMaterialByTone.get(tone);
      if (!glowMaterial) {
        glowMaterial = new THREE.SpriteMaterial({
          map: glowTexture,
          color: colorByTone[tone],
          transparent: true,
          opacity: tone === 'observed' || tone === 'conflict' ? 0.52 : 0.34,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        glowMaterialByTone.set(tone, glowMaterial);
      }
      if (position) {
        const glow = new THREE.Sprite(glowMaterial);
        glow.position.copy(position);
        glow.scale.setScalar(type === 'candidate' ? 1.25 : 0.9);
        scene.add(glow);
      }
      const mesh = new THREE.Mesh(nodeGeometry, material);
      if (position) mesh.position.copy(position);
      const scale = type === 'candidate' ? 1.9 : type === 'evidence' ? 1.32 : 1.12;
      mesh.scale.setScalar(scale);
      mesh.userData.node = node;
      nodeMeshes.push(mesh);
      scene.add(mesh);

      if (node.id === candidateNode?.id) {
        const position = positions.get(node.id);
        const contextCanvas = document.createElement('canvas');
        contextCanvas.width = 512;
        contextCanvas.height = 112;
        const context = contextCanvas.getContext('2d');
        if (position && context) {
          const text = node.label.length > 28 ? `${node.label.slice(0, 27)}…` : node.label;
          context.clearRect(0, 0, contextCanvas.width, contextCanvas.height);
          context.fillStyle = 'rgba(7, 11, 16, 0.92)';
          context.fillRect(34, 15, 444, 82);
          context.lineWidth = 2;
          context.strokeStyle = 'rgba(245, 247, 251, 0.24)';
          context.strokeRect(34, 15, 444, 82);
          context.font = '700 44px system-ui, sans-serif';
          context.textAlign = 'center';
          context.textBaseline = 'middle';
          context.shadowColor = colorByTone[tone];
          context.shadowBlur = 5;
          context.fillStyle = colorByTone[tone];
          context.fillText(text, contextCanvas.width / 2, 56, 410);
          const texture = new THREE.CanvasTexture(contextCanvas);
          texture.colorSpace = THREE.SRGBColorSpace;
          texture.generateMipmaps = false;
          texture.minFilter = THREE.LinearFilter;
          texture.magFilter = THREE.LinearFilter;
          const labelMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false, depthWrite: false });
          nodeLabelMaterials.push(labelMaterial);
          const sprite = new THREE.Sprite(labelMaterial);
          sprite.position.copy(position).add(new THREE.Vector3(0, 0.92, 0));
          sprite.scale.set(Math.min(3.8, Math.max(2.8, text.length * 0.28)), 1.16, 1);
          sprite.renderOrder = 3;
          scene.add(sprite);
        }
      }
    }

    const candidatePosition = candidateNode ? positions.get(candidateNode.id) : undefined;
    let candidateRing: THREE.Mesh | undefined;
    if (candidatePosition) {
      candidateRing = new THREE.Mesh(
        new THREE.TorusGeometry(0.44, 0.012, 8, 64),
        new THREE.MeshBasicMaterial({ color: '#f5f7fb', transparent: true, opacity: 0.78 }),
      );
      candidateRing.position.copy(candidatePosition);
      candidateRing.rotation.x = Math.PI / 2;
      scene.add(candidateRing);
    }

    const edgePositions: number[] = [];
    const edgeColors: number[] = [];
    for (const edge of edges) {
      const from = positions.get(edge.source);
      const to = positions.get(edge.target);
      if (!from || !to) continue;
      const color = new THREE.Color(relationshipColor(edge.type));
      edgePositions.push(from.x, from.y, from.z, to.x, to.y, to.z);
      edgeColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
    }
    const edgeGeometry = new THREE.BufferGeometry();
    edgeGeometry.setAttribute('position', new THREE.Float32BufferAttribute(edgePositions, 3));
    edgeGeometry.setAttribute('color', new THREE.Float32BufferAttribute(edgeColors, 3));
    const edgeMesh = new THREE.LineSegments(edgeGeometry, new THREE.LineBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.78, depthWrite: false,
    }));
    scene.add(edgeMesh);

    let arrows: THREE.InstancedMesh | undefined;
    if (edges.length > 0) {
      const arrowGeometry = new THREE.ConeGeometry(0.12, 0.36, 8);
      const arrowMaterial = new THREE.MeshBasicMaterial({ color: '#ffffff', vertexColors: true, transparent: true, opacity: 0.82, depthWrite: false });
      arrows = new THREE.InstancedMesh(arrowGeometry, arrowMaterial, edges.length);
      const arrowTransform = new THREE.Object3D();
      const arrowUp = new THREE.Vector3(0, 1, 0);
      edges.forEach((edge, index) => {
        const from = positions.get(edge.source);
        const to = positions.get(edge.target);
        if (!from || !to) return;
        const direction = to.clone().sub(from);
        arrowTransform.position.copy(from).addScaledVector(direction, 0.8);
        arrowTransform.quaternion.setFromUnitVectors(arrowUp, direction.normalize());
        arrowTransform.scale.setScalar(0.9);
        arrowTransform.updateMatrix();
        arrows?.setMatrixAt(index, arrowTransform.matrix);
        arrows?.setColorAt(index, new THREE.Color(relationshipColor(edge.type)));
      });
      arrows.instanceMatrix.needsUpdate = true;
      if (arrows.instanceColor) arrows.instanceColor.needsUpdate = true;
      scene.add(arrows);
    }

    const raycaster = new THREE.Raycaster();
    raycaster.params.Points = { threshold: 0.2 };
    const pointer = new THREE.Vector2();
    let pointerDown: { x: number; y: number } | null = null;
    function intersectNode(event: PointerEvent) {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      return raycaster.intersectObjects(nodeMeshes, false)[0]?.object ?? null;
    }
    function onPointerMove(event: PointerEvent) {
      if (event.buttons !== 0) return;
      const hit = intersectNode(event);
      const node = hit?.userData.node as CEGNode | undefined;
      setHoveredNode(previous => previous?.id === node?.id ? previous : node ?? null);
      renderer.domElement.style.cursor = node ? 'pointer' : 'grab';
    }
    function onPointerDown(event: PointerEvent) {
      pointerDown = { x: event.clientX, y: event.clientY };
    }
    function onPointerUp(event: PointerEvent) {
      if (!pointerDown) return;
      const moved = Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y);
      pointerDown = null;
      if (moved > 5) return;
      const hit = intersectNode(event);
      const node = hit?.userData.node as CEGNode | undefined;
      if (!node) return;
      setActiveNode(node);
      setHoveredNode(node);
      onSelectNodeRef.current(node);
    }
    function clearHover() {
      setHoveredNode(null);
      renderer.domElement.style.cursor = 'grab';
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove);
    renderer.domElement.addEventListener('pointerdown', onPointerDown);
    renderer.domElement.addEventListener('pointerup', onPointerUp);
    renderer.domElement.addEventListener('pointerleave', clearHover);

    resetViewRef.current = () => {
      camera.position.copy(restingPosition);
      controls.target.copy(center);
      controls.update();
    };

    const render = () => {
      if (disposed || !visible) return;
      controls.update();
      renderer.render(scene, camera);
      frame = window.requestAnimationFrame(render);
    };
    renderer.render(scene, camera);
    frame = window.requestAnimationFrame(render);

    const resizeObserver = new ResizeObserver(() => {
      if (!visible || !host.clientWidth || !host.clientHeight) return;
      renderer.setSize(host.clientWidth, host.clientHeight, false);
      camera.aspect = host.clientWidth / host.clientHeight;
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    });
    resizeObserver.observe(host);
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting && !contextLost;
      if (visible && !frame) frame = window.requestAnimationFrame(render);
      if (!visible && frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
    }, { threshold: 0.05 });
    visibilityObserver.observe(host);

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frame);
      visibilityObserver.disconnect();
      resizeObserver.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', onContextLost, false);
      renderer.domElement.removeEventListener('pointermove', onPointerMove);
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('pointerup', onPointerUp);
      renderer.domElement.removeEventListener('pointerleave', clearHover);
      nodeGeometry.dispose();
      for (const material of materialByTone.values()) material.dispose();
      for (const material of nodeLabelMaterials) {
        material.map?.dispose();
        material.dispose();
      }
      edgeGeometry.dispose();
      (edgeMesh.material as THREE.Material).dispose();
      for (const material of glowMaterialByTone.values()) material.dispose();
      glowTexture.dispose();
      arrows?.geometry.dispose();
      (arrows?.material as THREE.Material | undefined)?.dispose();
      candidateRing?.geometry.dispose();
      (candidateRing?.material as THREE.Material | undefined)?.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
      resetViewRef.current = null;
    };
  }, [graph]);

  const selectedNode = hoveredNode ?? activeNode;

  return (
    <div className={styles.viewer}>
      <div className={styles.viewport} ref={hostRef}>
        {webglUnavailable && <div className={styles.webglFallback} role="status">
          <strong>3D rendering is unavailable in this browser.</strong>
          <span>Use the searchable text equivalent below to inspect every returned node and relationship.</span>
        </div>}
        {selectedNode && !webglUnavailable && <div className={styles.nodeReadout} aria-live="polite">
          <span>{typeLabel(selectedNode.type)}</span>
          <strong>{selectedNode.label}</strong>
          {typeof selectedNode.properties.artifact_path === 'string' && <code>{selectedNode.properties.artifact_path}</code>}
        </div>}
        <div className={styles.viewportTag} aria-hidden="true">LIVE GRAPH DATA <i /> {Math.min(graph.nodes.length, MAX_3D_NODES)} / {graph.nodes.length} NODES</div>
      </div>
      <div className={styles.viewerFooter}>
        <p>Node color follows returned semantics. Position separates node types; connecting lines are only returned graph relationships.</p>
        <button type="button" className={styles.resetButton} disabled={webglUnavailable} onClick={() => resetViewRef.current?.()}>Reset view</button>
      </div>
      {selectedNode && <aside className={styles.nodeInspector} aria-label="Selected graph node details">
        <div className={styles.nodeInspectorHeading}>
          <span>{typeLabel(selectedNode.type)}</span>
          <h3>{selectedNode.label}</h3>
          <code>{selectedNode.id}</code>
        </div>
        <dl>
          {Object.entries(selectedNode.properties).slice(0, 8).map(([key, value]) => <div key={key}>
            <dt>{key.replaceAll('_', ' ')}</dt><dd>{propertyValue(value)}</dd>
          </div>)}
        </dl>
      </aside>}
      <p className={styles.srOnly}>Interactive 3D view of the returned Candidate Evidence Graph. Keyboard and screen reader users can open the text equivalent below to search and select each node and relationship.</p>
    </div>
  );
}
