import * as THREE from 'three';

export type SignalScene = { setPaused: (paused: boolean) => void; setVisible: (visible: boolean) => void; dispose: () => void };

/** Decorative scene only: no candidate data or implied live analysis. */
export function createSignalScene(host: HTMLElement, labels: HTMLElement[], onUnavailable: () => void): SignalScene {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('webgl2', { alpha: true, antialias: true, powerPreference: 'low-power' });
  if (!context) throw new Error('WebGL is unavailable');
  const renderer = new THREE.WebGLRenderer({ canvas, context, alpha: true, antialias: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.6));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  host.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(38, 1, .1, 40);
  camera.position.set(0, 0, 10);
  const world = new THREE.Group();
  scene.add(world);
  scene.add(new THREE.AmbientLight(0xc5b5ff, 1.5));
  const key = new THREE.DirectionalLight(0xe4dcff, 4);
  key.position.set(-3, 5, 4);
  scene.add(key);
  const rim = new THREE.PointLight(0x7ccfe4, 35, 15);
  rim.position.set(3, -1, 3);
  scene.add(rim);

  const core = new THREE.Group();
  world.add(core);
  const crystal = new THREE.IcosahedronGeometry(1.06, 0);
  const shell = new THREE.Mesh(crystal, new THREE.MeshPhysicalMaterial({ color: 0x8570bc, metalness: .48, roughness: .27, clearcoat: 1, transparent: true, opacity: .72, flatShading: true, emissive: 0x281740, emissiveIntensity: .32 }));
  core.add(shell);
  core.add(new THREE.LineSegments(new THREE.EdgesGeometry(crystal), new THREE.LineBasicMaterial({ color: 0xdfc9ff, transparent: true, opacity: .55 })));
  const cageGeometry = new THREE.IcosahedronGeometry(1.28, 0);
  const cage = new THREE.LineSegments(new THREE.EdgesGeometry(cageGeometry), new THREE.LineBasicMaterial({ color: 0xb3a0eb, transparent: true, opacity: .28 }));
  cageGeometry.dispose();
  world.add(cage);

  // A tilted meridian makes the front/back depth legible as the core rotates.
  const orbit = new THREE.Group();
  orbit.rotation.set(1.05, .25, -.35);
  world.add(orbit);
  const orbitPoints = Array.from({ length: 161 }, (_, i) => new THREE.Vector3(Math.cos(i / 160 * Math.PI * 2) * 1.65, Math.sin(i / 160 * Math.PI * 2) * 1.65, 0));
  orbit.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(orbitPoints), new THREE.LineBasicMaterial({ color: 0x9484bf, transparent: true, opacity: .3 })));
  const orbitSpark = new THREE.Mesh(new THREE.SphereGeometry(.045, 8, 8), new THREE.MeshBasicMaterial({ color: 0xe5d5ff }));
  orbit.add(orbitSpark);

  const positions = [new THREE.Vector3(-2.45, 1.45, .2), new THREE.Vector3(2.35, 1.05, -.25), new THREE.Vector3(1.95, -1.65, .5), new THREE.Vector3(-2.3, -1.45, -.15)];
  const colors = [0x84dce5, 0xc1dfa2, 0xc2a8f4, 0xe5c28b];
  const nodeGeometry = new THREE.OctahedronGeometry(.18, 0);
  const packetGeometry = new THREE.SphereGeometry(.032, 8, 6);
  const nodes = positions.map((position, index) => {
    const group = new THREE.Group();
    group.position.copy(position);
    const material = new THREE.MeshStandardMaterial({ color: colors[index], metalness: .45, roughness: .22, emissive: colors[index], emissiveIntensity: .18 });
    group.add(new THREE.Mesh(nodeGeometry, material));
    const outline = new THREE.LineSegments(new THREE.EdgesGeometry(nodeGeometry), new THREE.LineBasicMaterial({ color: colors[index], transparent: true, opacity: .35 }));
    outline.scale.setScalar(1.6);
    group.add(outline);
    world.add(group);
    const curve = new THREE.CubicBezierCurve3(position, position.clone().multiplyScalar(.75).add(new THREE.Vector3(0, .6, 1.1)), new THREE.Vector3(position.x * .25, -.35, 1), new THREE.Vector3());
    world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(64)), new THREE.LineBasicMaterial({ color: colors[index], transparent: true, opacity: .26 })));
    const packets = Array.from({ length: 4 }, () => {
      const packet = new THREE.Mesh(packetGeometry, new THREE.MeshBasicMaterial({ color: colors[index], transparent: true, opacity: .85 }));
      world.add(packet);
      return packet;
    });
    return { group, outline, curve, packets };
  });

  // Deterministic points avoid a changing layout on re-mount and need no assets.
  const dust = new Float32Array(150 * 3);
  for (let i = 0; i < 150; i++) {
    const angle = i * 2.399963;
    const radius = 1.5 + ((i * 37) % 100) / 100 * 1.55;
    dust[i * 3] = Math.cos(angle) * radius;
    dust[i * 3 + 1] = Math.sin(angle) * radius * .8;
    dust[i * 3 + 2] = Math.sin(i * 17) * 1.5;
  }
  const dustGeometry = new THREE.BufferGeometry();
  dustGeometry.setAttribute('position', new THREE.BufferAttribute(dust, 3));
  const particles = new THREE.Points(dustGeometry, new THREE.PointsMaterial({ color: 0xb1a4d9, size: .018, transparent: true, opacity: .48, sizeAttenuation: true }));
  world.add(particles);

  let paused = true;
  let visible = false;
  let disposed = false;
  let lost = false;
  let frame = 0;
  let time = 0;
  let last = 0;
  let width = 1;
  let height = 1;
  let labelWidths = labels.map(label => label.offsetWidth);
  const pointer = new THREE.Vector2();
  const projected = new THREE.Vector3();

  function draw() {
    if (disposed || lost) return;
    core.rotation.set(.2 + time * .13, time * .2, .14);
    cage.rotation.set(-.2 - time * .06, .4 + time * .1, -.12);
    particles.rotation.y = time * .025;
    orbitSpark.position.set(Math.cos(time * .45) * 1.65, Math.sin(time * .45) * 1.65, 0);
    world.rotation.x += (pointer.y * .11 - world.rotation.x) * .04;
    world.rotation.y += (pointer.x * .16 - world.rotation.y) * .04;
    nodes.forEach((node, index) => {
      node.group.rotation.set(time * .3, time * .4 + index, .2);
      node.outline.rotation.y = -time * .2;
      node.packets.forEach((packet, offset) => {
        const progress = (time * .12 + offset / 4 + index * .12) % 1;
        node.curve.getPoint(index < 2 ? progress : 1 - progress, packet.position);
        packet.scale.setScalar(.6 + Math.sin(progress * Math.PI) * .7);
      });
    });
    renderer.render(scene, camera);
    nodes.forEach((node, index) => {
      node.group.getWorldPosition(projected).project(camera);
      const label = labels[index];
      const x = Math.max(4, Math.min(width - labelWidths[index] - 4, (projected.x * .5 + .5) * width - labelWidths[index] / 2));
      const y = (-projected.y * .5 + .5) * height + 22;
      label.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    });
  }
  function tick(now: number) {
    frame = 0;
    if (disposed || lost || paused || !visible || document.hidden) return;
    // Cap decorative motion at 30 fps and don't advance after a background pause.
    if (now - last >= 1000 / 30) {
      time += Math.min((now - last) / 1000, .05);
      last = now;
      draw();
    }
    frame = requestAnimationFrame(tick);
  }
  function schedule() {
    cancelAnimationFrame(frame);
    frame = 0;
    last = performance.now();
    if (!disposed && !lost && !paused && visible && !document.hidden) frame = requestAnimationFrame(tick);
  }
  function resize() {
    if (disposed || lost) return;
    width = Math.max(1, host.clientWidth);
    height = Math.max(1, host.clientHeight);
    labelWidths = labels.map(label => label.offsetWidth);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    draw();
  }
  function move(event: PointerEvent) {
    if (paused || event.pointerType === 'touch') return;
    const rect = host.getBoundingClientRect();
    pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, (event.clientY - rect.top) / rect.height * 2 - 1);
  }
  function leave() { pointer.set(0, 0); }
  function contextLost(event: Event) {
    event.preventDefault();
    lost = true;
    paused = true;
    schedule();
    renderer.domElement.style.display = 'none';
    labels.forEach(label => { label.style.transform = ''; });
    host.dataset.renderer = 'fallback';
    onUnavailable();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  host.addEventListener('pointermove', move);
  host.addEventListener('pointerleave', leave);
  document.addEventListener('visibilitychange', schedule);
  renderer.domElement.addEventListener('webglcontextlost', contextLost);
  resize();
  void document.fonts.ready.then(resize);

  return {
    setPaused(value) { paused = value; schedule(); },
    setVisible(value) { visible = value; schedule(); },
    dispose() {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      host.removeEventListener('pointermove', move);
      host.removeEventListener('pointerleave', leave);
      document.removeEventListener('visibilitychange', schedule);
      renderer.domElement.removeEventListener('webglcontextlost', contextLost);
      const geometries = new Set<THREE.BufferGeometry>([crystal, nodeGeometry, packetGeometry]);
      const materials = new Set<THREE.Material>();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          geometries.add(object.geometry);
          (Array.isArray(object.material) ? object.material : [object.material]).forEach(material => materials.add(material));
        }
      });
      geometries.forEach(geometry => geometry.dispose());
      materials.forEach(material => material.dispose());
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
