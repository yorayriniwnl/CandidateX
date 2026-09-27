import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

export type SignalScene = {
  setPaused: (paused: boolean) => void;
  setVisible: (visible: boolean) => void;
  setStage: (stage: number) => void;
  triggerSurprise: () => void;
  dispose: () => void;
};

const THEMES = [
  {
    name: 'QUANTUM RESONANCE',
    label: 'Harmonic stream',
    colorA: [0.26, 0.08, 0.85],
    colorB: [0.17, 0.65, 0.95],
    primaryHex: 0x9872ff,
    secondaryHex: 0x8deaff,
    sparkHex: 0xcbb7ff,
    attenuation: 0x9a75ee,
  },
  {
    name: 'SOLAR SUPERNOVA',
    label: 'Thermonuclear surge',
    colorA: [0.98, 0.28, 0.04],
    colorB: [1.0, 0.82, 0.12],
    primaryHex: 0xff6b35,
    secondaryHex: 0xffd166,
    sparkHex: 0xffea79,
    attenuation: 0xff5522,
  },
  {
    name: 'CYBER EMERALD',
    label: 'Matrix verification',
    colorA: [0.01, 0.72, 0.45],
    colorB: [0.08, 0.88, 0.98],
    primaryHex: 0x10b981,
    secondaryHex: 0x06b6d4,
    sparkHex: 0x6ee7b7,
    attenuation: 0x059669,
  },
  {
    name: 'NEBULA HYPERDRIVE',
    label: 'Singularity overdrive',
    colorA: [0.92, 0.04, 0.68],
    colorB: [0.42, 0.16, 0.98],
    primaryHex: 0xf43f5e,
    secondaryHex: 0xa855f7,
    sparkHex: 0xf472b6,
    attenuation: 0xdb2777,
  },
];

/** Procedural product sculpture. All signals are illustrative, never candidate data. */
export function createSignalScene(
  host: HTMLElement,
  labels: HTMLElement[],
  onUnavailable: () => void,
  onSurprise?: (info: { name: string; label: string }) => void,
): SignalScene {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('webgl2', { alpha: true, antialias: true, powerPreference: 'default' });
  if (!context) throw new Error('WebGL is unavailable');
  const renderer = new THREE.WebGLRenderer({ canvas, context, alpha: true, antialias: true });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, .1, 50);
  camera.position.set(0, 0, 10.7);
  const world = new THREE.Group();
  world.rotation.order = 'YXZ';
  scene.add(world);

  // Broad studio reflections, generated locally: no textures or network requests.
  const studio = new THREE.Scene();
  studio.background = new THREE.Color(0x151522);
  const softboxGeometry = new THREE.PlaneGeometry(1, 1);
  const studioMaterials: THREE.Material[] = [];
  function softbox(color: number, intensity: number, position: [number, number, number], scale: [number, number]) {
    const material = new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(intensity), side: THREE.DoubleSide });
    studioMaterials.push(material);
    const panel = new THREE.Mesh(softboxGeometry, material);
    panel.position.set(...position);
    panel.scale.set(scale[0], scale[1], 1);
    panel.lookAt(0, 0, 0);
    studio.add(panel);
  }
  softbox(0xf0eeff, 5, [-3, 4, 3], [3, 6]);
  softbox(0x9b78ff, 4, [4, 0, -2], [2, 5]);
  softbox(0xa3eaff, 3, [-4, -2, -1], [1, 5]);
  softbox(0xffffff, 3, [0, -4, 3], [5, .5]);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const environment = pmrem.fromScene(studio, .035, .1, 30);
  scene.environment = environment.texture;
  softboxGeometry.dispose();
  studioMaterials.forEach(material => material.dispose());
  pmrem.dispose();

  const key = new THREE.DirectionalLight(0xeae7ff, 3.5);
  key.position.set(-3, 5, 5);
  scene.add(key);
  const violetLight = new THREE.PointLight(0x9872ff, 38, 12);
  violetLight.position.set(2, 1, 2);
  scene.add(violetLight);
  const iceLight = new THREE.PointLight(0x8deaff, 22, 12);
  iceLight.position.set(-3, -2, 2);
  scene.add(iceLight);
  const titanium = new THREE.MeshPhysicalMaterial({ color: 0x9a96ad, metalness: 1, roughness: .23, clearcoat: 1, clearcoatRoughness: .16, envMapIntensity: 1.1 });
  const darkMetal = new THREE.MeshStandardMaterial({ color: 0x282337, metalness: .92, roughness: .3 });
  const luminous = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x9470ff).multiplyScalar(2.7) });
  const ice = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x96e6ff).multiplyScalar(2) });

  // Articulated titanium rings with machined tick marks and luminous inlays.
  const rings = [2.1, 1.76, 1.43].map((radius, index) => {
    const group = new THREE.Group();
    group.add(new THREE.Mesh(new THREE.TorusGeometry(radius, index === 0 ? .075 : .055, 12, 160), titanium));
    group.add(new THREE.Mesh(new THREE.TorusGeometry(radius - .105, .018, 8, 160), darkMetal));
    const arc = new THREE.Mesh(new THREE.TorusGeometry(radius - .105, .012, 8, 128, Math.PI * 1.42), index === 1 ? ice : luminous);
    arc.rotation.z = index * 2.3;
    group.add(arc);
    const ticks = new THREE.InstancedMesh(new THREE.BoxGeometry(.009, .065, .012), titanium, 96);
    const transform = new THREE.Object3D();
    for (let tick = 0; tick < 96; tick++) {
      const angle = tick / 96 * Math.PI * 2;
      transform.position.set(Math.cos(angle) * (radius + .14), Math.sin(angle) * (radius + .14), 0);
      transform.rotation.z = angle - Math.PI / 2;
      transform.scale.set(1, tick % 8 === 0 ? 1.9 : 1, 1);
      transform.updateMatrix();
      ticks.setMatrixAt(tick, transform.matrix);
    }
    group.add(ticks);
    const bead = new THREE.Mesh(new THREE.SphereGeometry(.045, 12, 8), index === 1 ? ice : luminous);
    group.add(bead);
    world.add(group);
    return { group, arc, bead, radius };
  });

  const core = new THREE.Group();
  world.add(core);
  const glassGeometry = new THREE.IcosahedronGeometry(.94, 1);
  const glassMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xb5a0ed, metalness: .05, roughness: .13, transmission: .94,
    thickness: 1.5, ior: 1.48, iridescence: .75, iridescenceIOR: 1.3,
    clearcoat: 1, attenuationColor: new THREE.Color(0x9a75ee), attenuationDistance: 1.5, envMapIntensity: 1.7,
  });
  core.add(new THREE.Mesh(glassGeometry, glassMaterial));
  core.add(new THREE.LineSegments(new THREE.EdgesGeometry(glassGeometry, 12), new THREE.LineBasicMaterial({ color: 0xc8b4ff, transparent: true, opacity: .22 })));
  const energy = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uStage: { value: 0 },
      uSurge: { value: 0 },
      uColorA: { value: new THREE.Vector3(0.26, 0.08, 0.85) },
      uColorB: { value: new THREE.Vector3(0.17, 0.65, 0.95) },
    },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vPosition;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        vPosition = position;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform float uTime;
      uniform float uStage;
      uniform float uSurge;
      uniform vec3 uColorA;
      uniform vec3 uColorB;
      varying vec3 vNormal;
      varying vec3 vPosition;
      void main() {
        float rim = pow(1.0 - abs(vNormal.z), 2.0);
        float ribbons = sin(vPosition.y * (18.0 + uSurge * 14.0) + sin(vPosition.x * 8.0 + uTime * (.7 + uSurge * 4.0)) * 2.0 - uTime * (1.0 + uSurge * 5.0));
        ribbons = pow(.5 + .5 * ribbons, 5.0);
        vec3 color = mix(uColorA, uColorB, clamp(vPosition.y + .35 + uStage * .09, 0.0, 1.0));
        color *= .65 + ribbons * (2.2 + uSurge * 4.0) + rim * (2.4 + uSurge * 2.5);
        gl_FragColor = vec4(color, 1.0);
      }`,
  });
  core.add(new THREE.Mesh(new THREE.SphereGeometry(.66, 48, 32), energy));
  const innerOrbit = new THREE.Mesh(new THREE.TorusGeometry(.78, .016, 8, 100), ice);
  innerOrbit.rotation.set(.9, .4, -.5);
  core.add(innerOrbit);

  const shockwaveGeo = new THREE.RingGeometry(0.12, 0.38, 72);
  const shockwaveMat = new THREE.MeshBasicMaterial({
    color: 0x9872ff,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const shockwave = new THREE.Mesh(shockwaveGeo, shockwaveMat);
  shockwave.rotation.x = Math.PI / 2.2;
  world.add(shockwave);

  const SPARK_COUNT = 150;
  const sparkPositions = new Float32Array(SPARK_COUNT * 3);
  const sparkVelocities = new Float32Array(SPARK_COUNT * 3);
  const sparkGeo = new THREE.BufferGeometry();
  sparkGeo.setAttribute('position', new THREE.BufferAttribute(sparkPositions, 3));
  const sparkMat = new THREE.PointsMaterial({
    color: 0xcbb7ff,
    size: 0.045,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const sparks = new THREE.Points(sparkGeo, sparkMat);
  world.add(sparks);

  const anchors = [new THREE.Vector3(-2.85, 1.32, .3), new THREE.Vector3(2.75, 1.18, -.1), new THREE.Vector3(-2.7, -1.35, -.2), new THREE.Vector3(2.8, -1.3, .3)];
  const packetGeometry = new THREE.SphereGeometry(.021, 6, 6);
  const streams = anchors.map((anchor, index) => {
    const curve = new THREE.CubicBezierCurve3(anchor, anchor.clone().multiplyScalar(.72).add(new THREE.Vector3(0, index < 2 ? .6 : -.6, 1)), new THREE.Vector3(anchor.x * .3, anchor.y * -.4, .9), new THREE.Vector3());
    world.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(curve.getPoints(80)), new THREE.LineBasicMaterial({ color: index % 2 ? 0xb599ff : 0x8bcbdc, transparent: true, opacity: .16 })));
    const packets = Array.from({ length: 7 }, () => {
      const packet = new THREE.Mesh(packetGeometry, index % 2 ? luminous : ice);
      world.add(packet);
      return packet;
    });
    return { curve, packets };
  });
  const dustPositions = new Float32Array(340 * 3);
  for (let i = 0; i < 340; i++) {
    const angle = i * 2.399963;
    const radius = 2.3 + ((i * 37) % 113) / 113 * 1.35;
    dustPositions[i * 3] = Math.cos(angle) * radius;
    dustPositions[i * 3 + 1] = Math.sin(angle) * radius * .78;
    dustPositions[i * 3 + 2] = Math.sin(i * 12.71) * 1.1 - 1;
  }
  const dustGeometry = new THREE.BufferGeometry();
  dustGeometry.setAttribute('position', new THREE.BufferAttribute(dustPositions, 3));
  const dust = new THREE.Points(dustGeometry, new THREE.PointsMaterial({ color: 0xaca4d8, size: .012, transparent: true, opacity: .48, depthWrite: false }));
  world.add(dust);

  const composer = new EffectComposer(renderer);
  const renderPass = new RenderPass(scene, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(600, 600), .35, .45, 1.3);
  const output = new OutputPass();
  composer.addPass(renderPass);
  composer.addPass(bloom);
  composer.addPass(output);
  host.appendChild(canvas);
  let paused = true;
  let visible = false;
  let disposed = false;
  let lost = false;
  let frame = 0;
  let time = 0;
  let last = 0;
  let width = 1;
  let height = 1;
  let stage = 0;
  let currentStage = 0;
  let scroll = 0;
  let currentScroll = 0;
  let ratio = 1;
  let slowFrames = 0;
  let labelSizes = labels.map(label => [label.offsetWidth, label.offsetHeight]);
  const pointer = new THREE.Vector2();
  const look = new THREE.Vector2();
  const projected = new THREE.Vector3();
  const dragRotation = new THREE.Vector2();
  let isDragging = false;
  let dragPointerId: number | null = null;
  let lastPointerX = 0;
  let lastPointerY = 0;
  let returnFrame = 0;
  let lastReturnTime = 0;

  let themeIndex = 0;
  let shockwaveProgress = 1;
  let sparkLife = 0;
  let coreSurge = 0;
  let bloomSurge = 0;
  let warpSpeedSurge = 0;
  const ringSurgeSpin = [0, 0, 0];
  const ringSurgeAngle = [0, 0, 0];

  function triggerSurprise() {
    if (disposed || lost) return;
    themeIndex = (themeIndex + 1) % THEMES.length;
    const theme = THEMES[themeIndex];

    violetLight.color.setHex(theme.primaryHex);
    iceLight.color.setHex(theme.secondaryHex);
    shockwaveMat.color.setHex(theme.primaryHex);
    sparkMat.color.setHex(theme.sparkHex);
    luminous.color.set(new THREE.Color(theme.primaryHex).multiplyScalar(2.7));
    ice.color.set(new THREE.Color(theme.secondaryHex).multiplyScalar(2));
    glassMaterial.attenuationColor.setHex(theme.attenuation);
    energy.uniforms.uColorA.value.set(...theme.colorA);
    energy.uniforms.uColorB.value.set(...theme.colorB);

    shockwaveProgress = 0;
    coreSurge = 1.0;
    bloomSurge = 1.0;
    warpSpeedSurge = 14.0;
    ringSurgeSpin[0] += 16;
    ringSurgeSpin[1] -= 22;
    ringSurgeSpin[2] += 14;

    sparkLife = 1.0;
    sparkMat.opacity = 1.0;
    for (let i = 0; i < SPARK_COUNT; i++) {
      sparkPositions[i * 3] = (Math.random() - 0.5) * 0.08;
      sparkPositions[i * 3 + 1] = (Math.random() - 0.5) * 0.08;
      sparkPositions[i * 3 + 2] = (Math.random() - 0.5) * 0.08;

      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      const speed = 2.4 + Math.random() * 4.6;
      sparkVelocities[i * 3] = Math.sin(phi) * Math.cos(theta) * speed;
      sparkVelocities[i * 3 + 1] = Math.sin(phi) * Math.sin(theta) * speed;
      sparkVelocities[i * 3 + 2] = Math.cos(phi) * speed;
    }
    sparkGeo.attributes.position.needsUpdate = true;

    onSurprise?.({ name: theme.name, label: theme.label });

    if (paused) {
      lastReturnTime = performance.now();
      cancelAnimationFrame(returnFrame);
      returnFrame = requestAnimationFrame(stepReturnWhilePaused);
    }
  }

  function stepReturnWhilePaused() {
    if (disposed || lost) return;
    const now = performance.now();
    const dt = Math.min((now - (lastReturnTime || now)) / 1000, 0.05);
    lastReturnTime = now;
    if (!isDragging) {
      dragRotation.x = THREE.MathUtils.damp(dragRotation.x, 0, 7, dt);
      dragRotation.y = THREE.MathUtils.damp(dragRotation.y, 0, 7, dt);
      if (Math.abs(dragRotation.x) < 0.001) dragRotation.x = 0;
      if (Math.abs(dragRotation.y) < 0.001) dragRotation.y = 0;
    }
    draw(false, dt);
    const hasMovement =
      dragRotation.x !== 0 ||
      dragRotation.y !== 0 ||
      shockwaveProgress < 1 ||
      sparkLife > 0 ||
      coreSurge > 0.005 ||
      bloomSurge > 0.005;
    if (hasMovement) {
      returnFrame = requestAnimationFrame(stepReturnWhilePaused);
    } else {
      returnFrame = 0;
      lastReturnTime = 0;
    }
  }

  function draw(advance = false, dt = 0.016) {
    if (disposed || lost) return;
    if (advance) {
      look.lerp(pointer, .055);
      currentStage = THREE.MathUtils.lerp(currentStage, stage, .045);
      currentScroll = THREE.MathUtils.lerp(currentScroll, scroll, .04);
      if (!isDragging) {
        dragRotation.x = THREE.MathUtils.damp(dragRotation.x, 0, 7, dt);
        dragRotation.y = THREE.MathUtils.damp(dragRotation.y, 0, 7, dt);
        if (Math.abs(dragRotation.x) < 0.001) dragRotation.x = 0;
        if (Math.abs(dragRotation.y) < 0.001) dragRotation.y = 0;
      }
    }

    if (shockwaveProgress < 1) {
      shockwaveProgress = Math.min(1, shockwaveProgress + dt * 1.6);
      shockwave.scale.setScalar(0.2 + Math.pow(shockwaveProgress, 0.6) * 8.5);
      shockwaveMat.opacity = Math.pow(1 - shockwaveProgress, 1.8) * 0.95;
    } else {
      shockwaveMat.opacity = 0;
    }

    if (sparkLife > 0) {
      sparkLife = Math.max(0, sparkLife - dt * 1.3);
      sparkMat.opacity = Math.pow(sparkLife, 1.5);
      const friction = Math.pow(0.92, dt * 60);
      for (let i = 0; i < SPARK_COUNT; i++) {
        sparkPositions[i * 3] += sparkVelocities[i * 3] * dt;
        sparkPositions[i * 3 + 1] += sparkVelocities[i * 3 + 1] * dt;
        sparkPositions[i * 3 + 2] += sparkVelocities[i * 3 + 2] * dt;
        sparkVelocities[i * 3] *= friction;
        sparkVelocities[i * 3 + 1] *= friction;
        sparkVelocities[i * 3 + 2] *= friction;
      }
      sparkGeo.attributes.position.needsUpdate = true;
    } else {
      sparkMat.opacity = 0;
    }

    coreSurge = THREE.MathUtils.damp(coreSurge, 0, 4.0, dt);
    bloomSurge = THREE.MathUtils.damp(bloomSurge, 0, 3.2, dt);
    warpSpeedSurge = THREE.MathUtils.damp(warpSpeedSurge, 0, 3.0, dt);
    ringSurgeSpin[0] = THREE.MathUtils.damp(ringSurgeSpin[0], 0, 4.0, dt);
    ringSurgeSpin[1] = THREE.MathUtils.damp(ringSurgeSpin[1], 0, 4.0, dt);
    ringSurgeSpin[2] = THREE.MathUtils.damp(ringSurgeSpin[2], 0, 4.0, dt);
    ringSurgeAngle[0] += ringSurgeSpin[0] * dt;
    ringSurgeAngle[1] += ringSurgeSpin[1] * dt;
    ringSurgeAngle[2] += ringSurgeSpin[2] * dt;

    bloom.strength = 0.35 + bloomSurge * 1.15;
    renderer.toneMappingExposure = 1.12 + bloomSurge * 0.35;

    world.rotation.set(
      dragRotation.x + look.y * .1 + currentScroll * .08,
      dragRotation.y + look.x * .17,
      -.07
    );

    const coreBounce = 1.0 + Math.sin(coreSurge * Math.PI) * 0.32;
    core.scale.setScalar(coreBounce);
    core.rotation.set(.16 + Math.sin(time * .17) * .08, time * .13, .14);
    energy.uniforms.uTime.value = time;
    energy.uniforms.uStage.value = currentStage;
    energy.uniforms.uSurge.value = coreSurge;
    innerOrbit.rotation.z = -.5 + time * .15;
    const spread = Math.sin(currentStage / 3 * Math.PI * .8) * .42;
    rings.forEach((ring, index) => {
      const angle = time * (.1 + index * .025) + ringSurgeAngle[index];
      ring.group.rotation.set(
        [.72, -.66, .28][index] + Math.sin(angle) * .12 + currentStage * .065,
        [-.42, .62, -.82][index] + Math.cos(angle * .7) * .1,
        [-.3, .55, -.5][index] + time * [.025, -.04, .035][index] + currentScroll * .15 + ringSurgeAngle[index] * 0.2,
      );
      ring.group.scale.setScalar((1 + spread * (index + 1) * .13) * (1 + coreSurge * 0.1));
      ring.group.position.y = (index - 1) * spread;
      ring.arc.rotation.z = index * 2.3 + time * .08 + ringSurgeAngle[index] * 0.5;
      ring.bead.position.set(Math.cos(angle * 2 + index) * ring.radius, Math.sin(angle * 2 + index) * ring.radius, 0);
    });
    streams.forEach((stream, index) => stream.packets.forEach((packet, offset) => {
      let progress = ((time + warpSpeedSurge * 0.2) * .075 + offset / 7 + index * .13) % 1;
      if (index % 2) progress = 1 - progress;
      stream.curve.getPoint(progress, packet.position);
      packet.scale.setScalar((.4 + Math.sin(progress * Math.PI) * 1.1) * (1 + coreSurge * 0.4));
    }));
    dust.rotation.z = time * .012;
    composer.render();
    anchors.forEach((anchor, index) => {
      if (!labels[index]) return;
      projected.copy(anchor).applyMatrix4(world.matrixWorld).project(camera);
      const [labelWidth, labelHeight] = labelSizes[index];
      const x = THREE.MathUtils.clamp((projected.x * .5 + .5) * width - labelWidth / 2, 8, width - labelWidth - 8);
      const y = THREE.MathUtils.clamp((-projected.y * .5 + .5) * height - labelHeight / 2, 8, height - labelHeight - 8);
      labels[index].style.transform = `translate3d(${x}px, ${y}px, 0)`;
    });
  }
  function tick(now: number) {
    frame = 0;
    if (disposed || lost || paused || !visible || document.hidden) return;
    const interval = width < 500 ? 1000 / 30 : 1000 / 60;
    if (now - last >= interval - 1) {
      const elapsed = now - last;
      const dt = Math.min(elapsed / 1000, .05);
      time += dt;
      last = now;
      draw(true, dt);
      // Reduce fill cost when the browser consistently misses its frame budget.
      slowFrames = elapsed > 48 ? slowFrames + 1 : Math.max(0, slowFrames - 1);
      if (slowFrames > 80 && ratio > 1) {
        ratio = 1;
        renderer.setPixelRatio(ratio);
        composer.setPixelRatio(ratio);
        slowFrames = 0;
      }
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
    labelSizes = labels.map(label => [label.offsetWidth, label.offsetHeight]);
    ratio = Math.min(window.devicePixelRatio, width < 500 ? 1.25 : 1.5);
    renderer.setPixelRatio(ratio);
    renderer.setSize(width, height, false);
    composer.setPixelRatio(ratio);
    composer.setSize(width, height);
    camera.aspect = width / height;
    camera.position.z = camera.aspect < 1 ? 10.7 / camera.aspect : 10.7;
    camera.updateProjectionMatrix();
    draw();
  }
  function onPointerDown(event: PointerEvent) {
    if (event.button !== 0 && event.pointerType === 'mouse') return;
    if (returnFrame) {
      cancelAnimationFrame(returnFrame);
      returnFrame = 0;
      lastReturnTime = 0;
    }
    isDragging = true;
    dragPointerId = event.pointerId;
    lastPointerX = event.clientX;
    lastPointerY = event.clientY;
    host.dataset.dragging = 'true';
    document.body.style.userSelect = 'none';
    try {
      host.setPointerCapture(event.pointerId);
    } catch {
      // Ignored
    }
  }
  function onPointerMove(event: PointerEvent) {
    if (isDragging && (dragPointerId === null || event.pointerId === dragPointerId)) {
      const deltaX = event.clientX - lastPointerX;
      const deltaY = event.clientY - lastPointerY;
      lastPointerX = event.clientX;
      lastPointerY = event.clientY;

      const rotSensitivityX = (Math.PI * 2) / (Math.max(width, 200) * 0.65);
      const rotSensitivityY = (Math.PI * 2) / (Math.max(height, 200) * 0.75);

      dragRotation.y += deltaX * rotSensitivityX;
      dragRotation.x += deltaY * rotSensitivityY;

      const maxPitch = Math.PI * 0.42;
      dragRotation.x = THREE.MathUtils.clamp(dragRotation.x, -maxPitch, maxPitch);

      draw(false);
    } else if (!paused && event.pointerType !== 'touch') {
      const rect = host.getBoundingClientRect();
      pointer.set((event.clientX - rect.left) / rect.width * 2 - 1, (event.clientY - rect.top) / rect.height * 2 - 1);
    }
  }
  function onPointerUp(event: PointerEvent) {
    if (isDragging && (dragPointerId === null || event.pointerId === dragPointerId)) {
      isDragging = false;
      dragPointerId = null;
      delete host.dataset.dragging;
      document.body.style.userSelect = '';
      try {
        if (host.hasPointerCapture(event.pointerId)) {
          host.releasePointerCapture(event.pointerId);
        }
      } catch {
        // Ignored
      }

      if (dragRotation.y > Math.PI * 2) {
        dragRotation.y = (dragRotation.y % (Math.PI * 2));
      } else if (dragRotation.y < -Math.PI * 2) {
        dragRotation.y = -((-dragRotation.y) % (Math.PI * 2));
      }

      if (paused) {
        lastReturnTime = performance.now();
        returnFrame = requestAnimationFrame(stepReturnWhilePaused);
      }
    }
  }
  function onLostPointerCapture(event: PointerEvent) {
    if (isDragging && event.pointerId === dragPointerId) {
      onPointerUp(event);
    }
  }
  function leave() {
    if (!isDragging) {
      pointer.set(0, 0);
    }
  }
  function onDragStart(event: DragEvent) {
    event.preventDefault();
  }
  function onContextMenu(event: MouseEvent) {
    event.preventDefault();
    triggerSurprise();
  }
  function onScroll() {
    if (paused || !visible) return;
    const rect = host.getBoundingClientRect();
    scroll = THREE.MathUtils.clamp(-rect.top / Math.max(rect.height, 1), 0, 1);
  }
  function contextLost(event: Event) {
    event.preventDefault();
    lost = true;
    schedule();
    if (returnFrame) {
      cancelAnimationFrame(returnFrame);
      returnFrame = 0;
    }
    document.body.style.userSelect = '';
    canvas.style.display = 'none';
    labels.forEach(label => { label.style.transform = ''; });
    host.dataset.renderer = 'fallback';
    onUnavailable();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  host.addEventListener('pointerdown', onPointerDown);
  host.addEventListener('pointermove', onPointerMove);
  host.addEventListener('pointerup', onPointerUp);
  host.addEventListener('pointercancel', onPointerUp);
  host.addEventListener('lostpointercapture', onLostPointerCapture);
  host.addEventListener('pointerleave', leave);
  host.addEventListener('dragstart', onDragStart);
  host.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerUp);
  window.addEventListener('scroll', onScroll, { passive: true });
  document.addEventListener('visibilitychange', schedule);
  canvas.addEventListener('webglcontextlost', contextLost);
  resize();
  void document.fonts.ready.then(resize);

  return {
    setPaused(value) {
      paused = value;
      if (returnFrame) {
        cancelAnimationFrame(returnFrame);
        returnFrame = 0;
        lastReturnTime = 0;
      }
      schedule();
    },
    setVisible(value) { visible = value; schedule(); },
    setStage(value) {
      stage = THREE.MathUtils.clamp(value, 0, 3);
      if (paused) { currentStage = stage; draw(); }
    },
    triggerSurprise,
    dispose() {
      disposed = true;
      cancelAnimationFrame(frame);
      if (returnFrame) cancelAnimationFrame(returnFrame);
      observer.disconnect();
      host.removeEventListener('pointerdown', onPointerDown);
      host.removeEventListener('pointermove', onPointerMove);
      host.removeEventListener('pointerup', onPointerUp);
      host.removeEventListener('pointercancel', onPointerUp);
      host.removeEventListener('lostpointercapture', onLostPointerCapture);
      host.removeEventListener('pointerleave', leave);
      host.removeEventListener('dragstart', onDragStart);
      host.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('pointercancel', onPointerUp);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('visibilitychange', schedule);
      canvas.removeEventListener('webglcontextlost', contextLost);
      document.body.style.userSelect = '';
      const geometries = new Set<THREE.BufferGeometry>();
      const materials = new Set<THREE.Material>();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line || object instanceof THREE.Points) {
          geometries.add(object.geometry);
          (Array.isArray(object.material) ? object.material : [object.material]).forEach(material => materials.add(material));
          if (object instanceof THREE.InstancedMesh) object.dispose();
        }
      });
      geometries.forEach(geometry => geometry.dispose());
      materials.forEach(material => material.dispose());
      environment.dispose();
      renderPass.dispose();
      bloom.dispose();
      output.dispose();
      composer.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    },
  };
}
