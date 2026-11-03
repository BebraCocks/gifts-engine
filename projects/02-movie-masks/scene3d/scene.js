// 3D-проход ролика 02-movie-masks: гримёрка → полёт сквозь зеркало → ночной пригород.
// Кадр — чистая функция времени t (секунды содержания). Никакого состояния между кадрами,
// кроме кэша текстур. Маска — 2D-карточка внутри сцены (кадры Lottie готовит Python).
import * as THREE from 'three';

const W = 1080, H = 1920;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0a0f24, 0.022);
const camera = new THREE.PerspectiveCamera(58, W / H, 0.05, 500);

// ---------- утилиты ----------
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R = rng(20261103);
const clamp01 = x => Math.min(1, Math.max(0, x));
const smooth = x => { x = clamp01(x); return x * x * (3 - 2 * x); };
const easeIn = x => { x = clamp01(x); return x * x * x; };
const easeOut = x => { x = clamp01(x); return 1 - Math.pow(1 - x, 3); };
const lerp = (a, b, k) => a + (b - a) * k;
const V = (x, y, z) => new THREE.Vector3(x, y, z);

function ctex(w, h, fn, rep = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  fn(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rep[0], rep[1]); t.anisotropy = 8;
  return t;
}
const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0, ...o });
function add(geo, mat, x, y, z, parent = scene, shadow = true) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true; parent.add(m); return m;
}
const box = (w, h, d, mat, x, y, z, p, s) => add(new THREE.BoxGeometry(w, h, d), mat, x, y, z, p, s);

const glowTex = ctex(128, 128, (g, w, h) => {
  const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.45)');
  gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
});
function glow(color, size, x, y, z, opacity = 0.7, parent = scene) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity, fog: false }));
  s.scale.set(size, size, 1); s.position.set(x, y, z); parent.add(s); return s;
}

// ---------- текстуры ----------
const woodTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#4a2a1a'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 8; i++) {
    const x = i * w / 8; g.fillStyle = `hsl(${18 + R() * 8},${40 + R() * 12}%,${16 + R() * 8}%)`; g.fillRect(x + 2, 0, w / 8 - 4, h);
    for (let k = 0; k < 30; k++) { g.strokeStyle = 'rgba(0,0,0,0.12)'; g.beginPath(); const xx = x + R() * w / 8; g.moveTo(xx, 0); g.lineTo(xx + R() * 6 - 3, h); g.stroke(); }
    g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x + ((i * 97) % 3) * 0, (i * 211) % h, w / 8, 3);
  }
}, [3, 4]);
const wallTex = ctex(256, 512, (g, w, h) => {
  g.fillStyle = '#4a0f1a'; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 64) { g.fillStyle = 'rgba(255,190,140,0.07)'; g.fillRect(x, 0, 22, h); }
  for (let y = 0; y < h; y += 64) for (let x = 0; x < w; x += 64) {
    g.fillStyle = 'rgba(255,200,150,0.08)'; g.beginPath(); g.ellipse(x + 43, y + 32, 9, 14, 0, 0, Math.PI * 2); g.fill();
  }
}, [6, 2]);
const grassTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#1f3a1e'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 9000; i++) { g.fillStyle = `hsla(${95 + R() * 30},${35 + R() * 25}%,${10 + R() * 18}%,0.8)`; g.fillRect(R() * w, R() * h, 2, 3 + R() * 4); }
}, [30, 24]);
const asphaltTex = ctex(512, 256, (g, w, h) => {
  g.fillStyle = '#1b1c22'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 6000; i++) { const v = 20 + R() * 30; g.fillStyle = `rgb(${v},${v},${v + 4})`; g.fillRect(R() * w, R() * h, 2, 2); }
  g.fillStyle = '#c9a646'; for (let x = 0; x < w; x += 128) g.fillRect(x, h / 2 - 4, 70, 8);
}, [20, 1]);
const concreteTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#6f6c68'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 2500; i++) { const v = 90 + R() * 40; g.fillStyle = `rgba(${v},${v},${v},0.5)`; g.fillRect(R() * w, R() * h, 2, 2); }
  g.strokeStyle = 'rgba(20,20,20,0.6)'; g.lineWidth = 3; g.strokeRect(0, 0, w, h);
}, [1, 1]);
const sidingTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#8ea0b4'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 16) { g.fillStyle = 'rgba(0,0,0,0.22)'; g.fillRect(0, y + 13, w, 3); g.fillStyle = 'rgba(255,255,255,0.08)'; g.fillRect(0, y, w, 2); }
}, [4, 3]);
const roofTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#25262d'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 20) for (let x = (y / 20) % 2 * 16; x < w; x += 32) { g.fillStyle = `rgba(0,0,0,${0.2 + R() * 0.25})`; g.fillRect(x, y, 30, 18); }
}, [6, 3]);

// ---------- небо ----------
const sky = new THREE.Mesh(new THREE.SphereGeometry(300, 32, 16), new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, fog: false,
  uniforms: { top: { value: new THREE.Color(0x04060f) }, mid: { value: new THREE.Color(0x1d1838) }, bot: { value: new THREE.Color(0x0a0c18) } },
  vertexShader: 'varying vec3 vp; void main(){ vp = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader: 'uniform vec3 top; uniform vec3 mid; uniform vec3 bot; varying vec3 vp; void main(){ float h = normalize(vp).y; vec3 c = h>0.0 ? mix(mid, top, pow(h,0.55)) : mix(mid, bot, pow(-h,0.4)); gl_FragColor = vec4(c,1.0); }',
}));
scene.add(sky);
{
  const n = 900, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const a = R() * Math.PI * 2, e = 0.12 + R() * 1.3, r = 280; pos[i * 3] = r * Math.cos(e) * Math.sin(a); pos[i * 3 + 1] = r * Math.sin(e); pos[i * 3 + 2] = r * Math.cos(e) * Math.cos(a); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  scene.add(new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xdfe6ff, size: 2.2, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85 })));
}
const moonTex = ctex(256, 256, (g, w, h) => {
  const gr = g.createRadialGradient(w * 0.45, h * 0.42, 10, w / 2, h / 2, w / 2);
  gr.addColorStop(0, '#fffbe8'); gr.addColorStop(0.85, '#e7e1c8'); gr.addColorStop(1, 'rgba(231,225,200,0)');
  g.fillStyle = gr; g.beginPath(); g.arc(w / 2, h / 2, w / 2 - 2, 0, Math.PI * 2); g.fill();
  for (let i = 0; i < 14; i++) { g.fillStyle = 'rgba(150,145,125,0.25)'; g.beginPath(); g.arc(50 + R() * 156, 50 + R() * 156, 6 + R() * 18, 0, Math.PI * 2); g.fill(); }
});
{
  const m = new THREE.Sprite(new THREE.SpriteMaterial({ map: moonTex, fog: false, depthWrite: false }));
  m.scale.set(22, 22, 1); m.position.set(-38, 82, -210); scene.add(m);
  glow(0x9fb6ff, 110, -38, 82, -212, 0.35);
}

// ---------- свет ----------
const hemi = new THREE.HemisphereLight(0x5a6aa8, 0x120c10, 0.55); scene.add(hemi);
const moon = new THREE.DirectionalLight(0xa9bcff, 1.25);
moon.position.set(-22, 34, -4); moon.target.position.set(0, 0, -26); scene.add(moon, moon.target);
moon.castShadow = true; moon.shadow.mapSize.set(2048, 2048);
Object.assign(moon.shadow.camera, { left: -28, right: 28, top: 30, bottom: -30, near: 1, far: 120 });
moon.shadow.bias = -0.0008; moon.shadow.normalBias = 0.02;

// ---------- гримёрка (z от 2 до -6) ----------
const room = new THREE.Group(); scene.add(room);
const floorMat = std(0xffffff, { map: woodTex, roughness: 0.55 });
add(new THREE.PlaneGeometry(6, 8.4).rotateX(-Math.PI / 2), floorMat, 0, 0, -1.9, room, false);
add(new THREE.PlaneGeometry(6, 8.4).rotateX(Math.PI / 2), std(0x1a0d10), 0, 3.2, -1.9, room);
const wallMat = std(0xffffff, { map: wallTex, roughness: 0.9 });
add(new THREE.PlaneGeometry(8.4, 3.2).rotateY(Math.PI / 2), wallMat, -3, 1.6, -1.9, room);
add(new THREE.PlaneGeometry(8.4, 3.2).rotateY(-Math.PI / 2), wallMat, 3, 1.6, -1.9, room);
add(new THREE.PlaneGeometry(6, 3.2).rotateY(Math.PI), wallMat, 0, 1.6, 2.3, room);
// задняя стена с проёмом-зеркалом x∈[-0.75,0.75], y∈[0.95,2.75]
const MX = 0.75, MY0 = 0.95, MY1 = 2.75, MZ = -6.0;
const backMat = std(0xffffff, { map: wallTex.clone(), roughness: 0.9 }); backMat.map.repeat.set(3, 2);
box(3 - MX, 3.2, 0.12, backMat, -(3 + MX) / 2, 1.6, MZ - 0.06, room);
box(3 - MX, 3.2, 0.12, backMat, (3 + MX) / 2, 1.6, MZ - 0.06, room);
box(2 * MX, MY0, 0.12, backMat, 0, MY0 / 2, MZ - 0.06, room);
box(2 * MX, 3.2 - MY1, 0.12, backMat, 0, (3.2 + MY1) / 2, MZ - 0.06, room);
const gold = std(0xc8a050, { metalness: 0.85, roughness: 0.3 });
box(2 * MX + 0.24, 0.12, 0.1, gold, 0, MY1 + 0.06, MZ + 0.02, room);
box(2 * MX + 0.24, 0.12, 0.1, gold, 0, MY0 - 0.06, MZ + 0.02, room);
box(0.12, MY1 - MY0 + 0.24, 0.1, gold, -MX - 0.06, (MY0 + MY1) / 2, MZ + 0.02, room);
box(0.12, MY1 - MY0 + 0.24, 0.1, gold, MX + 0.06, (MY0 + MY1) / 2, MZ + 0.02, room);
const bulbs = [];
const bulbMat = new THREE.MeshBasicMaterial({ color: 0xffe6b0 });
function bulb(x, y) { add(new THREE.SphereGeometry(0.045, 12, 8), bulbMat, x, y, MZ + 0.09, room, false); bulbs.push(glow(0xffb45c, 0.42, x, y, MZ + 0.12, 0.55, room)); }
for (let k = 0; k < 6; k++) { const y = MY0 + 0.12 + k * (MY1 - MY0 - 0.24) / 5; bulb(-MX - 0.06, y); bulb(MX + 0.06, y); }
for (let k = 1; k < 5; k++) bulb(-MX + k * (2 * MX) / 5, MY1 + 0.06);
// столик и мелочи
const tableMat = std(0x2b1710, { roughness: 0.5 });
box(2.8, 0.08, 0.75, tableMat, 0, 0.8, MZ + 0.42, room);
box(2.6, 0.74, 0.6, std(0x1c0f0b), 0, 0.38, MZ + 0.36, room);
const propCols = [0xb2263a, 0xe0c27a, 0x3b6fb5, 0xf2efe8, 0x7a2a8a];
for (let k = 0; k < 7; k++) {
  const x = -1.25 + k * 0.38 + (k > 2 ? 0.55 : 0) - (k > 3 ? 0.4 : 0);
  if (Math.abs(x) < 0.5) continue;
  const h = 0.12 + R() * 0.2;
  add(new THREE.CylinderGeometry(0.04 + R() * 0.03, 0.05, h, 16), std(propCols[k % 5], { roughness: 0.3, metalness: 0.2 }), x, 0.84 + h / 2, MZ + 0.35 + R() * 0.2, room);
}
// афиши на боковых стенах
for (const [x, ry, z, c] of [[-2.98, Math.PI / 2, -3.2, 0xd8b26a], [2.98, -Math.PI / 2, -2.4, 0x9a3a3a], [-2.98, Math.PI / 2, -0.4, 0x4a6aa0]]) {
  const p = add(new THREE.PlaneGeometry(1.0, 1.4), std(c, { roughness: 0.7 }), x, 1.7, z, room, false); p.rotation.y = ry;
  const f = add(new THREE.PlaneGeometry(1.12, 1.52), std(0x120806), x - Math.sign(x) * -0.005, 1.7, z, room, false); f.rotation.y = ry; f.position.x += Math.sign(x) * 0.006;
}
const warmA = new THREE.PointLight(0xffb870, 9, 9, 1.6); warmA.position.set(-0.95, 1.95, MZ + 0.35);
const warmB = new THREE.PointLight(0xffb870, 9, 9, 1.6); warmB.position.set(0.95, 1.95, MZ + 0.35);
const warmC = new THREE.PointLight(0xffc890, 5, 10, 1.6); warmC.position.set(0, 2.9, MZ + 0.4);
const fill = new THREE.PointLight(0xff8a5a, 2.2, 12, 1.8); fill.position.set(1.6, 2.6, 0.6);
room.add(warmA, warmB, warmC, fill);

// силуэт: голова, шея, плечи-капсула, грудь; контровой свет из зеркала
const silMat = std(0x1a1a20, { roughness: 0.32, metalness: 0.35 });
const sil = new THREE.Group(); sil.position.set(0, 0, -4.3); room.add(sil);
add(new THREE.SphereGeometry(0.17, 40, 28), silMat, 0, 1.6, 0, sil).scale.set(1, 1.24, 1.06);
add(new THREE.CylinderGeometry(0.062, 0.075, 0.22, 24), silMat, 0, 1.37, 0, sil);
add(new THREE.CapsuleGeometry(0.11, 0.42, 8, 24).rotateZ(Math.PI / 2), silMat, 0, 1.2, 0, sil).scale.set(1, 1, 0.9);
add(new THREE.SphereGeometry(0.5, 40, 28), silMat, 0, 0.98, 0, sil).scale.set(0.62, 0.62, 0.36);
const rim = new THREE.SpotLight(0xffc488, 60, 6, 0.6, 0.5, 1.5); rim.position.set(0, 2.2, -5.75); rim.target.position.set(0, 1.4, -4.3); room.add(rim, rim.target);
const rim2 = new THREE.SpotLight(0xffb070, 25, 5, 0.5, 0.6, 1.5); rim2.position.set(-0.7, 1.4, -5.7); rim2.target.position.set(0, 1.3, -4.3); room.add(rim2, rim2.target);
// стекло зеркала: лёгкий блик, сквозь него видна ночь; вспышка при пролёте
const glassTex = ctex(256, 512, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, 'rgba(255,255,255,0.0)'); gr.addColorStop(0.42, 'rgba(255,255,255,0.0)');
  gr.addColorStop(0.5, 'rgba(255,255,255,0.35)'); gr.addColorStop(0.56, 'rgba(255,255,255,0.0)'); gr.addColorStop(0.66, 'rgba(255,255,255,0.18)'); gr.addColorStop(0.7, 'rgba(255,255,255,0)');
  g.fillStyle = 'rgba(150,170,210,0.18)'; g.fillRect(0, 0, w, h); g.fillStyle = gr; g.fillRect(0, 0, w, h);
});
const glass = add(new THREE.PlaneGeometry(2 * MX, MY1 - MY0), new THREE.MeshBasicMaterial({ map: glassTex, transparent: true, depthWrite: false, fog: false }), 0, (MY0 + MY1) / 2, MZ - 0.01, room, false);
const flash = glow(0xcfe0ff, 3.5, 0, 1.86, MZ - 0.3, 0);

// ---------- пригород (z < -6.2) ----------
const town = new THREE.Group(); scene.add(town);
add(new THREE.PlaneGeometry(160, 92).rotateX(-Math.PI / 2), std(0xffffff, { map: grassTex, roughness: 0.95 }), 0, 0, -52.2, town, false);
add(new THREE.PlaneGeometry(160, 6).rotateX(-Math.PI / 2), std(0xffffff, { map: asphaltTex, roughness: 0.7 }), 0, 0.012, -12.5, town, false);
const swMat = std(0xffffff, { map: concreteTex.clone(), roughness: 0.85 }); swMat.map.repeat.set(80, 1);
add(new THREE.PlaneGeometry(160, 1.8).rotateX(-Math.PI / 2), swMat, 0, 0.02, -16.4, town, false);
add(new THREE.PlaneGeometry(160, 1.8).rotateX(-Math.PI / 2), swMat, 0, 0.02, -8.6, town, false);
const pathMat = std(0xffffff, { map: concreteTex.clone(), roughness: 0.85 }); pathMat.map.repeat.set(1, 10);
add(new THREE.PlaneGeometry(1.5, 13.6).rotateX(-Math.PI / 2), pathMat, 0, 0.022, -24.1, town, false);

function house(x, z, w, d, hBody, sidingColor, roofColor, lit, parent = town, detail = true) {
  const g = new THREE.Group(); g.position.set(x, 0, z); parent.add(g);
  const sMat = std(sidingColor, { map: sidingTex, roughness: 0.85 });
  box(w, hBody, d, sMat, 0, hBody / 2, 0, g);
  const rMat = std(roofColor, { map: roofTex, roughness: 0.75 });
  const slope = Math.atan2(2.6, d / 2), len = Math.hypot(2.6, d / 2) + 0.4;
  const r1 = box(w + 0.6, 0.18, len, rMat, 0, hBody + 1.3, d / 4, g); r1.rotation.x = slope;
  const r2 = box(w + 0.6, 0.18, len, rMat, 0, hBody + 1.3, -d / 4, g); r2.rotation.x = -slope;
  const gable = new THREE.Shape(); gable.moveTo(-d / 2, 0); gable.lineTo(d / 2, 0); gable.lineTo(0, 2.6); gable.lineTo(-d / 2, 0);
  for (const sx of [-1, 1]) { const m = add(new THREE.ShapeGeometry(gable), sMat, sx * w / 2, hBody, 0, g); m.rotation.y = sx * Math.PI / 2; }
  if (!detail) return g;
  const front = d / 2 + 0.01;
  const frame = std(0xe8e4dc, { roughness: 0.6 });
  const winLit = new THREE.MeshBasicMaterial({ color: 0xffc77a });
  const winRed = new THREE.MeshBasicMaterial({ color: 0xff6a3d });
  const winDark = std(0x0c1222, { roughness: 0.15, metalness: 0.6 });
  const wins = [[-3.6, 1.6], [-1.9, 1.6], [1.9, 1.6], [3.6, 1.6], [-3.6, 4.6], [-1.3, 4.6], [1.3, 4.6], [3.6, 4.6]];
  wins.forEach(([wx, wy], k) => {
    if (Math.abs(wx) > w / 2 - 0.6) return;
    box(1.12, 1.46, 0.1, frame, wx, wy, front, g, false);
    const state = lit[k] || 0;
    const mat = state === 1 ? winLit : state === 2 ? winRed : winDark;
    add(new THREE.PlaneGeometry(0.9, 1.24), mat, wx, wy, front + 0.06, g, false);
    box(0.06, 1.24, 0.04, frame, wx, wy, front + 0.08, g, false);
    if (state) { glow(state === 1 ? 0xffb35c : 0xff5a2a, 2.6, wx, wy, front + 0.4, 0.42, g); const pl = new THREE.PointLight(state === 1 ? 0xffb066 : 0xff5a2a, 3.5, 6, 2); pl.position.set(wx, wy, front + 0.8); g.add(pl); }
  });
  return g;
}
const hero = house(0, -36, 11, 8, 6.2, 0x9fb0c4, 0x2a2b33, [1, 0, 0, 1, 0, 2, 0, 0]);
// дверь, крыльцо, колонны, фонарь
box(1.15, 2.25, 0.12, std(0x5a1f1a, { roughness: 0.5 }), 0, 1.45, -31.94, hero.parent);
box(5.2, 0.32, 2.4, std(0x6a5a50), 0, 0.16, -30.8);
for (let k = 0; k < 3; k++) box(1.8, 0.11, 0.35, std(0x77685e), 0, 0.055 + k * 0.105, -29.45 + k * -0.3 + 0.6);
for (const sx of [-2.3, 2.3]) add(new THREE.CylinderGeometry(0.12, 0.14, 2.75, 20), std(0xece8e0), sx, 1.7, -29.8);
box(5.6, 0.16, 2.8, std(0x2a2b33), 0, 3.1, -30.8);
glow(0xffd08a, 1.4, 0, 2.65, -31.75, 0.75);
const porch = new THREE.PointLight(0xffc27a, 8, 9, 1.7); porch.position.set(0, 2.6, -31.2); scene.add(porch);
house(-17, -40, 10, 8, 5.4, 0x7d6a5c, 0x2b2626, [0, 1, 0, 0, 0, 0, 1, 0]).rotation.y = 0.12;
house(17.5, -39, 10, 8, 5.4, 0xa7a49a, 0x25262c, [0, 0, 1, 0, 1, 0, 0, 0]).rotation.y = -0.1;
house(-33, -46, 10, 8, 5, 0x6a7782, 0x232428, [0, 0, 0, 0, 0, 1, 0, 0]).rotation.y = 0.25;
house(33, -45, 10, 8, 5, 0x8a7a68, 0x232428, [0, 1, 0, 0, 0, 0, 0, 0]).rotation.y = -0.25;
for (let k = 0; k < 8; k++) house(-45 + k * 13, 4 - 80 - R() * 6, 9, 7, 4.6, 0x3a3f48, 0x1b1c20, [], town, false);
// забор
{
  const picket = new THREE.BoxGeometry(0.09, 0.95, 0.04);
  const pm = std(0xe9e6df, { roughness: 0.7 });
  const xs = []; for (let x = -15; x <= 15; x += 0.24) if (Math.abs(x) > 1.1) xs.push(x);
  const inst = new THREE.InstancedMesh(picket, pm, xs.length); inst.castShadow = true; inst.receiveShadow = true;
  const m = new THREE.Matrix4(); xs.forEach((x, i) => { m.makeTranslation(x, 0.475, -17.6); inst.setMatrixAt(i, m); }); town.add(inst);
  for (const sx of [-1, 1]) { box(13.9, 0.07, 0.05, pm, sx * 8.05, 0.3, -17.63); box(13.9, 0.07, 0.05, pm, sx * 8.05, 0.72, -17.63); }
}
// деревья
function tree(x, z, s) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.scale.setScalar(s); town.add(g);
  add(new THREE.CylinderGeometry(0.18, 0.28, 3.2, 10), std(0x2a1d16), 0, 1.6, 0, g);
  const leaf = std(0x173320, { roughness: 0.9, flatShading: true });
  for (const [lx, ly, lz, r] of [[0, 3.8, 0, 1.6], [0.9, 3.3, 0.3, 1.1], [-0.8, 3.4, -0.2, 1.2], [0.1, 4.7, 0.1, 1.1]]) add(new THREE.IcosahedronGeometry(r, 1), leaf, lx, ly, lz, g);
  return g;
}
tree(-8.2, -27, 1.25); tree(8.6, -25.5, 1.1); tree(-12.5, -21, 0.9); tree(12.8, -22, 1.0); tree(-25, -30, 1.3); tree(26, -31, 1.2); tree(5.5, -46, 1.4); tree(-6, -47, 1.5);
// почтовый ящик
add(new THREE.CylinderGeometry(0.04, 0.04, 1.0, 8), std(0x2a2a2a), 1.5, 0.5, -17.2);
box(0.26, 0.24, 0.48, std(0x30415e, { metalness: 0.4, roughness: 0.4 }), 1.5, 1.08, -17.2);
// фонари
function streetLamp(x, z) {
  add(new THREE.CylinderGeometry(0.07, 0.1, 5.4, 10), std(0x1e2026, { metalness: 0.6, roughness: 0.4 }), x, 2.7, z);
  box(0.9, 0.08, 0.1, std(0x1e2026), x + 0.4 * Math.sign(-x), 5.35, z);
  glow(0xffe0a8, 2.4, x + 0.8 * Math.sign(-x), 5.2, z, 0.8);
  const sp = new THREE.SpotLight(0xffd59a, 40, 18, 0.8, 0.6, 1.6);
  sp.position.set(x + 0.8 * Math.sign(-x), 5.2, z); sp.target.position.set(x + 0.8 * Math.sign(-x), 0, z); scene.add(sp, sp.target);
}
streetLamp(-6.5, -9.2); streetLamp(7.5, -9.2); streetLamp(-24, -9.2); streetLamp(24, -9.2);

// ---------- маска ----------
const maskTex = new THREE.Texture(); maskTex.colorSpace = THREE.SRGBColorSpace;
const maskMat = new THREE.MeshBasicMaterial({ map: maskTex, transparent: true, side: THREE.DoubleSide, toneMapped: false, fog: false, depthWrite: false });
const mask = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), maskMat); mask.renderOrder = 10; scene.add(mask);
const shadowTex = ctex(128, 128, (g, w, h) => { const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2); gr.addColorStop(0, 'rgba(0,0,0,0.85)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
const blob = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }));
blob.position.y = 0.03; scene.add(blob);
const maskLight = new THREE.PointLight(0xff3030, 0, 6, 1.5); scene.add(maskLight);

const imgCache = new Map();
function loadImg(url) {
  if (!imgCache.has(url)) imgCache.set(url, new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = url; }));
  if (imgCache.size > 64) imgCache.delete(imgCache.keys().next().value);
  return imgCache.get(url);
}

// ---------- траектории (кубический Эрмит с касательными Катмулла–Рома по времени) ----------
function track(keys) {
  return t => {
    if (t <= keys[0][0]) return keys[0][1].clone();
    const n = keys.length; if (t >= keys[n - 1][0]) return keys[n - 1][1].clone();
    let i = 0; while (keys[i + 1][0] < t) i++;
    const [t0, p0, s0] = keys[i], [t1, p1, s1] = keys[i + 1], dt = t1 - t0, u = (t - t0) / dt;
    const tan = j => { if (keys[j][2] === 'stop' || j === 0 || j === n - 1) return V(0, 0, 0); return keys[j + 1][1].clone().sub(keys[j - 1][1]).divideScalar(keys[j + 1][0] - keys[j - 1][0]); };
    const m0 = tan(i).multiplyScalar(dt), m1 = tan(i + 1).multiplyScalar(dt);
    const u2 = u * u, u3 = u2 * u;
    return p0.clone().multiplyScalar(2 * u3 - 3 * u2 + 1).add(m0.multiplyScalar(u3 - 2 * u2 + u)).add(p1.clone().multiplyScalar(-2 * u3 + 3 * u2)).add(m1.multiplyScalar(u3 - u2));
  };
}
const FACE = V(0, 1.6, -4.11);
const camPos = track([
  [0.0, V(0, 1.72, 0.9), 'stop'], [3.2, V(0, 1.66, -2.35)], [4.3, V(0, 1.64, -2.8)],
  [4.78, V(0, 2.06, -3.95)], [5.08, V(0, 1.86, -6.0)], [5.5, V(0.2, 3.5, -11.6)],
  [6.15, V(0.6, 2.0, -16.7)], [10.0, V(1.0, 1.42, -18.9), 'stop'],
]);
const camLook = track([
  [0.0, V(0, 1.6, -4.3), 'stop'], [4.3, V(0, 1.6, -4.3)], [4.78, V(0, 1.82, -7.0)],
  [5.08, V(0, 1.9, -11.0)], [5.5, V(0, 1.7, -22.0)], [6.15, V(0, 1.55, -24.0)], [10.0, V(0, 1.55, -24.2), 'stop'],
]);
const maskFlight = track([
  [4.3, FACE.clone(), 'stop'], [4.75, V(0, 1.78, -5.7)], [5.1, V(0, 2.0, -9.0)], [5.5, V(0, 2.6, -15.5)], [6.1, V(0, 1.6, -24.0), 'stop'],
]);

function setState(t) {
  // камера + удар при посадке маски
  const p = camPos(t), l = camLook(t);
  const hit = t > 3.2 ? Math.exp(-(t - 3.2) * 7) : 0;
  p.x += Math.sin(t * 61) * 0.022 * hit; p.y += Math.sin(t * 47 + 1) * 0.018 * hit;
  camera.position.copy(p); camera.lookAt(l);
  camera.rotation.z += Math.sin(t * 39) * 0.012 * hit;
  camera.fov = 58 + 8 * smooth((t - 4.55) / 0.35) * (1 - smooth((t - 5.35) / 0.7)); camera.updateProjectionMatrix();

  // свет гримёрки: красная вспышка на «МАНЬЯК»
  const red = t > 3.2 ? Math.exp(-(t - 3.2) * 2.2) * (0.75 + 0.25 * Math.sin(t * 40)) : 0;
  for (const L of [warmA, warmB]) L.color.setRGB(1, lerp(0.72, 0.12, red), lerp(0.44, 0.08, red));
  for (const b of bulbs) b.material.color.setRGB(1, lerp(0.7, 0.15, red), lerp(0.36, 0.1, red));

  // маска
  let mp, size = 0.46, spin = 0, vis = t >= 2.0;
  if (t < 3.2) {
    const k = clamp01((t - 2.0) / 1.2);
    mp = V(0, 2.3, -14).lerp(FACE, easeIn(k));
    spin = (1 - easeOut(k)) * Math.PI * 4;
  } else if (t < 4.3) {
    mp = FACE.clone();
    size = 0.46 * (1 + 0.14 * Math.exp(-(t - 3.2) * 9) * Math.cos((t - 3.2) * 30));
  } else {
    mp = maskFlight(t);
    const k = smooth((t - 4.3) / 1.8);
    size = lerp(0.46, 1.5, k);
    if (t > 6.1) { const s = t - 6.1; size *= 1 + 0.08 * Math.exp(-s * 5) * Math.cos(s * 16); mp.y += Math.sin((t - 6.1) * 1.6) * 0.05; }
    spin = t > 6.1 ? Math.sin((t - 6.1) * 0.9) * 0.14 : -Math.PI * 2 * smooth((t - 4.4) / 1.6);
  }
  mask.visible = vis;
  mask.position.copy(mp); mask.scale.set(size, size, 1);
  mask.quaternion.copy(camera.quaternion);
  mask.rotateY(spin);
  // тень-пятно на траве
  const inTown = mp.z < -6.5;
  blob.visible = vis && inTown;
  blob.position.set(mp.x, 0.03, mp.z); const bs = size * 1.1 * (1.2 - Math.min(1, (mp.y - size / 2) / 4) * 0.5); blob.scale.set(bs, 1, bs * 0.6);
  blob.material.opacity = 0.65 * smooth((t - 5.6) / 0.5);
  maskLight.position.copy(mp).add(V(0, 0, 0.5)); maskLight.intensity = 0;
  // стекло: дрожит перед пролётом, вспышка в момент прохода
  const cross = Math.exp(-Math.pow((t - 5.04) / 0.05, 2));
  glass.material.opacity = 1 - smooth((t - 4.95) / 0.12);
  flash.material.opacity = 0.4 * cross; flash.scale.setScalar(2.5 + 2.5 * cross);
}

const acc = document.createElement('canvas'); acc.width = W; acc.height = H;
const actx = acc.getContext('2d');

// Время → кадр Lottie (60 fps, 180 кадров). Сдвиг фазы: кровь (1,2–2,1 с цикла) совпадает с «МАНЬЯК».
window.MASK = { name: 'ghostface', frames: 180, fps: 60, offset: 0.9 };
window.renderAt = async (t) => {
  const M = window.MASK;
  const idx = Math.floor(((t + M.offset) * M.fps) + 1e-6) % M.frames;
  const im = await loadImg(`/masks/${M.name}/${String(idx).padStart(3, '0')}.png`);
  if (maskTex.image !== im) { maskTex.image = im; maskTex.needsUpdate = true; }
  // скорость камеры → число подкадров для смаза движения (выдержка 1/2 кадра)
  const dt = 1 / 60, a = camPos(t - dt / 2), b = camPos(t + dt / 2);
  const speed = a.distanceTo(b) / dt;
  const N = speed < 1.5 ? 1 : Math.min(10, Math.ceil(speed / 1.6));
  const shutter = 0.5 / 60;
  for (let k = 0; k < N; k++) {
    const tk = N === 1 ? t : t + ((k + 0.5) / N - 0.5) * shutter;
    setState(tk); renderer.render(scene, camera);
    actx.globalAlpha = 1 / (k + 1); actx.drawImage(renderer.domElement, 0, 0);
  }
  actx.globalAlpha = 1;
  return acc.toDataURL('image/png');
};
window.READY = true;
