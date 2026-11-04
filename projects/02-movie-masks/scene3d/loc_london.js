// Локация 2: ночной Лондон над Темзой — парламент, часовая башня, мост, фейерверки 5 ноября,
// отражения в воде, лепестки роз. Маска Anonymous. После рекламы лепестки летят в камеру.
import * as THREE from 'three';
import { rng, clamp01, smooth, easeIn, lerp, V, ctex, std, add, box, glow, skyDome, stars, track, makeMask, rig, newCamera } from './common.js';

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0b1022, 0.0045);
const camera = newCamera();
const R = rng(5111605);
skyDome(scene, 0x050814, 0x1a2140, 0x060810);
stars(scene, R, 250);

scene.add(new THREE.HemisphereLight(0x5f6fae, 0x0a0a12, 0.5));
const moonL = new THREE.DirectionalLight(0x9fb2ff, 0.6); moonL.position.set(40, 80, 60); scene.add(moonL);

// ---------- текстуры ----------
const facadeTex = ctex(512, 256, (g, w, h) => {
  g.fillStyle = '#b98a45'; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 16) { g.fillStyle = 'rgba(70,40,10,0.35)'; g.fillRect(x, 0, 3, h); }
  for (let y = 18; y < h - 10; y += 34) for (let x = 5; x < w; x += 16) {
    const lit = R() < 0.45; g.fillStyle = lit ? '#ffd889' : '#3b2a18';
    g.beginPath(); g.moveTo(x, y + 22); g.lineTo(x, y + 6); g.lineTo(x + 3, y); g.lineTo(x + 6, y + 6); g.lineTo(x + 6, y + 22); g.fill();
  }
  g.fillStyle = 'rgba(60,35,10,0.5)'; for (let y = 0; y < h; y += 34) g.fillRect(0, y, w, 3);
}, [6, 1]);
const stoneTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#5e5446'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 24) for (let x = (y / 24) % 2 * 20; x < w; x += 40) { g.strokeStyle = 'rgba(0,0,0,0.35)'; g.strokeRect(x, y, 40, 24); }
}, [30, 1]);
const clockTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#1c1408'; g.fillRect(0, 0, w, h);
  const c = w / 2; const gr = g.createRadialGradient(c, c, 10, c, c, 118); gr.addColorStop(0, '#fff6d8'); gr.addColorStop(1, '#f0d48a');
  g.fillStyle = gr; g.beginPath(); g.arc(c, c, 112, 0, Math.PI * 2); g.fill();
  g.strokeStyle = '#2b1c08'; g.lineWidth = 6; g.stroke();
  for (let k = 0; k < 12; k++) { const a = k * Math.PI / 6; g.lineWidth = 6; g.beginPath(); g.moveTo(c + Math.sin(a) * 92, c - Math.cos(a) * 92); g.lineTo(c + Math.sin(a) * 106, c - Math.cos(a) * 106); g.stroke(); }
  g.lineWidth = 8; g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.sin(3.6) * 55, c - Math.cos(3.6) * 55); g.stroke();
  g.lineWidth = 5; g.beginPath(); g.moveTo(c, c); g.lineTo(c + Math.sin(5.0) * 85, c - Math.cos(5.0) * 85); g.stroke();
});
const waterTex = ctex(256, 512, (g, w, h) => {
  g.fillStyle = 'rgba(0,0,0,0)'; g.clearRect(0, 0, w, h);
  for (let i = 0; i < 260; i++) { g.fillStyle = `rgba(160,190,255,${0.05 + R() * 0.12})`; g.fillRect(R() * w, R() * h, 18 + R() * 50, 2); }
}, [30, 10]);

// ---------- набережная, парламент, башня, мост (с зеркальной копией для отражения) ----------
const city = new THREE.Group(); scene.add(city);
const facade = std(0xffffff, { map: facadeTex, emissive: 0xffffff, emissiveMap: facadeTex, emissiveIntensity: 0.55, roughness: 0.9 });
const stone = std(0xffffff, { map: stoneTex, roughness: 0.95 });
const roofM = std(0x2a2d34, { roughness: 0.6, metalness: 0.3 });
const goldLit = std(0xd8a24c, { emissive: 0xffc36a, emissiveIntensity: 0.6, roughness: 0.6 });
box(city, 260, 3.2, 8, stone, -10, 1.6, -80, false);
box(city, 104, 22, 14, facade, -23, 14, -92, false);
const ridge = add(city, new THREE.CylinderGeometry(0.1, 7.5, 6, 4, 1).rotateY(Math.PI / 4), roofM, -15, 28, -92, false); ridge.scale.set(11, 1, 1);
for (let x = -72; x <= 42; x += 13) {
  box(city, 3.2, 31, 3.2, goldLit, x, 15.5, -84.4, false);
  add(city, new THREE.ConeGeometry(2.6, 7, 4).rotateY(Math.PI / 4), roofM, x, 34.5, -84.4, false);
  for (const dx of [-1.6, 1.6]) add(city, new THREE.ConeGeometry(0.5, 3, 4), goldLit, x + dx, 32.5, -82.8, false);
}
box(city, 9, 34, 9, facade, -15, 17, -95, false);
add(city, new THREE.ConeGeometry(6, 16, 8), roofM, -15, 42, -95, false);
box(city, 16, 54, 16, facade, -82, 27, -94, false);
for (const [dx, dz] of [[-7, -7], [7, -7], [-7, 7], [7, 7]]) add(city, new THREE.ConeGeometry(1.2, 7, 4), goldLit, -82 + dx, 57, -94 + dz, false);
// часовая башня
const TX = 34, TZ = -82;
box(city, 9, 50, 9, facade, TX, 25, TZ, false);
box(city, 11, 10, 11, goldLit, TX, 55, TZ, false);
const clockM = std(0xffffff, { map: clockTex, emissive: 0xffffff, emissiveMap: clockTex, emissiveIntensity: 1.1 });
for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2; const p = add(city, new THREE.PlaneGeometry(8.4, 8.4), clockM, TX + Math.sin(a) * 5.56, 55, TZ + Math.cos(a) * 5.56, false); p.rotation.y = a; }
box(city, 9, 7, 9, facade, TX, 63.5, TZ, false);
add(city, new THREE.ConeGeometry(7, 20, 4).rotateY(Math.PI / 4), roofM, TX, 77, TZ, false);
add(city, new THREE.ConeGeometry(0.7, 6, 8), goldLit, TX, 89, TZ, false);
// мост
const bridgeM = std(0x2e5a48, { roughness: 0.7 });
box(city, 16, 2, 150, bridgeM, 88, 9, -10, false);
for (let z = -70; z <= 50; z += 24) {
  box(city, 14, 9, 4, stone, 88, 4.5, z, false);
}
for (let z = -76; z <= 60; z += 9) { glow(city, 0xffe1a0, 3.2, 81, 13, z, 0.85); glow(city, 0xffe1a0, 3.2, 95, 13, z, 0.85); }
for (let x = -130; x <= 70; x += 11) glow(city, 0xffd690, 3.6, x, 6.5, -76, 0.8);
// дальние кварталы
for (let k = 0; k < 40; k++) {
  const x = -260 + k * 13 + R() * 6, h = 14 + R() * 30;
  box(city, 10 + R() * 6, h, 10, std(0x151a2a, { emissive: 0x1a1408, emissiveIntensity: 0.2 }), x, h / 2, -150 - R() * 40, false);
}
const mirror = city.clone(); mirror.scale.y = -1; mirror.position.y = -0.02; scene.add(mirror);

// вода поверх отражения
const water = add(scene, new THREE.PlaneGeometry(900, 140).rotateX(-Math.PI / 2), new THREE.MeshStandardMaterial({ color: 0x07122a, roughness: 0.75, metalness: 0.1, transparent: true, opacity: 0.8 }), 0, 0, -5, false);
const ripple = add(scene, new THREE.PlaneGeometry(900, 140).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: waterTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.7 }), 0, 0.05, -5, false);
box(scene, 900, 2.2, 6, stone, 0, 1.1, 68, false);           // ближняя набережная

// ---------- фейерверки ----------
const BURSTS = [];
{
  const cols = [0xff3b3b, 0xffd35a, 0xffffff, 0x62ff9a, 0xff7ad9, 0x6ab8ff];
  let t = 15.5;
  while (t < 24.3) { BURSTS.push({ t0: t, p: V(-70 + R() * 130, 46 + R() * 34, -105 - R() * 25), c: new THREE.Color(cols[Math.floor(R() * cols.length)]), n: 110, seed: Math.floor(R() * 1e6), sp: 9 + R() * 6 }); t += 0.45 + R() * 0.55; }
}
const MAXP = 4 * 110 * 6;
const fwGeo = new THREE.BufferGeometry();
const fwPos = new Float32Array(MAXP * 3), fwCol = new Float32Array(MAXP * 3);
fwGeo.setAttribute('position', new THREE.BufferAttribute(fwPos, 3)); fwGeo.setAttribute('color', new THREE.BufferAttribute(fwCol, 3));
const dotTex = ctex(64, 64, (g, w, h) => { const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.4, 'rgba(255,255,255,0.6)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 64, 64); });
const fwMat = new THREE.PointsMaterial({ size: 1.5, map: dotTex, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false });
const fw = new THREE.Points(fwGeo, fwMat); fw.frustumCulled = false; scene.add(fw);
const fwMirror = new THREE.Points(fwGeo, fwMat.clone()); fwMirror.material.opacity = 0.35; fwMirror.scale.y = -1; fwMirror.frustumCulled = false; scene.add(fwMirror);
const flashL = new THREE.PointLight(0xffffff, 0, 260, 1.2); scene.add(flashL);
function fireworks(t) {
  let n = 0; let flash = 0;
  for (const b of BURSTS) {
    const age = t - b.t0; if (age < 0 || age > 2.2) continue;
    const r = rng(b.seed);
    for (let i = 0; i < b.n; i++) {
      const th = r() * Math.PI * 2, ph = Math.acos(2 * r() - 1), sp = b.sp * (0.75 + 0.25 * r());
      const dir = V(Math.sin(ph) * Math.cos(th), Math.cos(ph), Math.sin(ph) * Math.sin(th));
      for (let k = 0; k < 4; k++) {
        const a = Math.max(0, age - k * 0.045); const drag = (1 - Math.exp(-a * 1.6)) / 1.6;
        const p = b.p.clone().addScaledVector(dir, sp * drag); p.y -= 2.2 * a * a;
        const fade = (1 - clamp01(age / 2.2)) ** 1.5 * (1 - k * 0.22) * (age < 0.05 ? age / 0.05 : 1);
        if (n >= MAXP) break;
        fwPos.set([p.x, p.y, p.z], n * 3); fwCol.set([b.c.r * fade, b.c.g * fade, b.c.b * fade], n * 3); n++;
      }
    }
    const f = Math.exp(-age * 3.5); if (f > flash) { flash = f; flashL.color.copy(b.c); flashL.position.copy(b.p); }
  }
  fwGeo.setDrawRange(0, n); fwGeo.attributes.position.needsUpdate = true; fwGeo.attributes.color.needsUpdate = true;
  flashL.intensity = 1400 * flash;
}

// ---------- лепестки роз ----------
const petalTex = ctex(64, 64, (g) => { g.fillStyle = '#c01828'; g.beginPath(); g.ellipse(32, 32, 26, 15, 0.4, 0, Math.PI * 2); g.fill(); g.fillStyle = 'rgba(255,90,100,0.6)'; g.beginPath(); g.ellipse(26, 28, 12, 6, 0.4, 0, Math.PI * 2); g.fill(); });
const petalMat = new THREE.MeshBasicMaterial({ map: petalTex, transparent: true, side: THREE.DoubleSide, depthWrite: false, fog: false });
const PETALS = [];
for (let i = 0; i < 160; i++) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), petalMat); m.frustumCulled = false; scene.add(m);
  PETALS.push({ m, x: (R() - 0.5) * 40, y: 2 + R() * 22, z: -40 + R() * 40, s: 0.35 + R() * 0.35, ph: R() * 6.28, burst: i < 110, bx: (R() - 0.5) * 2.2, by: (R() - 0.5) * 3.2, bd: 0.6 + R() * 0.8 });
}
const MASKP = V(0, 7, -25);
function petals(t, cam) {
  for (const p of PETALS) {
    let pos;
    if (p.burst && t > 24.0) {
      // после рекламы: лепестки срываются с маски и летят в камеру
      const k = easeIn(clamp01((t - 24.0 - p.ph * 0.012) / (0.45 * p.bd)));
      const start = MASKP.clone().add(V(p.bx * 2, p.by, 0.5));
      const end = cam.clone().add(V(p.bx * 0.6, p.by * 0.4, -0.6));
      pos = start.lerp(end, k);
      p.m.visible = true; p.m.scale.setScalar(p.s * (1.4 + 2.5 * k));
    } else if (!p.burst) {
      const fall = (t * 0.9 + p.ph * 3) % 24;
      pos = V(p.x + Math.sin(t * 0.8 + p.ph) * 1.2, p.y + 12 - fall, p.z);
      p.m.visible = pos.y > 0.2; p.m.scale.setScalar(p.s);
    } else { p.m.visible = false; continue; }
    p.m.position.copy(pos);
    p.m.rotation.set(t * 2 + p.ph, t * 1.3 + p.ph * 2, p.ph);
  }
}

// ---------- маска и камера ----------
const mask = makeMask(scene);
const camPos = track([
  [15.3, V(0, 62, 95)], [16.4, V(0, 15, 32)], [19.6, V(-7, 7.8, 2)], [22.6, V(4, 7.3, -6)], [23.85, V(3, 7.2, -9), 'stop'],
  [24.0, V(3, 7.2, -9.1)], [24.5, V(1.2, 7.1, -17.5)],
]);
const camLook = track([
  [15.3, V(0, 42, -100)], [16.4, V(0, 18, -90)], [19.6, V(0, 8.5, -25), 'stop'], [22.6, V(0, 7.2, -25)], [23.85, V(0, 7.2, -25), 'stop'],
  [24.0, V(0, 7.2, -25)], [24.5, V(0, 7.0, -30)],
]);
const RG = rig(camera, camPos, camLook, t => 58 + 8 * smooth((t - 24.1) / 0.4));

function setState(t) {
  RG.set(t);
  fireworks(t);
  petals(t, camera.position);
  ripple.material.map.offset.set(t * 0.02, t * 0.05);
  const size = 5.2 * (t < 16.4 ? lerp(0.6, 1, smooth((t - 15.3) / 1.1)) : 1);
  const mp = MASKP.clone(); mp.y += Math.sin(t * 1.4) * 0.12;
  mask.pose(camera, mp, size, 1, Math.sin(t * 0.7) * 0.12);
}

export default {
  name: 'london', scene, camera, bursts: BURSTS.map(b => b.t0),
  async prepare(t) { await mask.load('anonymous', t); },
  set: setState,
  speed: t => RG.speed(t),
};
