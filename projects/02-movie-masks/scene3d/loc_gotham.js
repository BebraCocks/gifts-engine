// Локация 5: крыша небоскрёба в Готэме ночью — дождь, огни башен, бэт-сигнал в облаках, молнии.
// Маска Dark Knight на парапете. Вход: камера смотрит вверх на сигнал и опускается; выход — полёт в луч.
import * as THREE from 'three';
import { rng, clamp01, smooth, easeIn, lerp, V, ctex, std, add, box, glow, skyDome, track, makeMask, rig, newCamera } from './common.js';

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0c1418, 0.0065);
const camera = newCamera();
const R = rng(1939);
const sky = skyDome(scene, 0x05080c, 0x16222a, 0x05070a, 600);

const hemi = new THREE.HemisphereLight(0x6f8fa8, 0x080a0c, 0.45); scene.add(hemi);
const key = new THREE.DirectionalLight(0x9fc0e0, 1.7); key.position.set(-30, 60, -40); key.target.position.set(0, 0, -8); scene.add(key, key.target);
key.castShadow = true; key.shadow.mapSize.set(1024, 1024); Object.assign(key.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 140 });
const lightning = new THREE.DirectionalLight(0xdde8ff, 0); lightning.position.set(40, 80, -80); scene.add(lightning);

// окна небоскрёбов
function winTex(seed, lit) {
  const r = rng(seed);
  return ctex(256, 512, (g, w, h) => {
    g.fillStyle = '#0d1216'; g.fillRect(0, 0, w, h);
    for (let y = 4; y < h; y += 14) for (let x = 4; x < w; x += 12) {
      const on = r() < lit; g.fillStyle = on ? `hsl(${38 + r() * 12},${70 + r() * 20}%,${55 + r() * 25}%)` : `rgba(40,60,70,${0.4 + r() * 0.3})`; g.fillRect(x, y, 8, 9);
    }
  });
}
const towerMats = [0.18, 0.28, 0.12, 0.35].map((lit, k) => { const t = winTex(77 + k, lit); return std(0xffffff, { map: t, emissive: 0xffffff, emissiveMap: t, emissiveIntensity: 0.9, roughness: 0.6, metalness: 0.3 }); });
const BASE = -120;
for (let i = 0; i < 170; i++) {
  const a = R() * Math.PI * 2, d = 26 + Math.pow(R(), 0.7) * 260;
  const x = Math.sin(a) * d, z = -Math.abs(Math.cos(a) * d) * (R() < 0.85 ? 1 : -0.3) - 10;
  if (Math.abs(x) < 14 && z > -30) continue;
  const w = 10 + R() * 18, h = 60 + R() * 200, dd = 10 + R() * 18;
  const m = towerMats[i % 4].clone(); m.map = m.map.clone(); m.map.repeat.set(w / 14, h / 28); m.emissiveMap = m.map; m.map.needsUpdate = true;
  const b = box(scene, w, h, dd, m, x, BASE + h / 2, z, false);
  if (R() < 0.3) add(scene, new THREE.ConeGeometry(w * 0.45, 18, 4).rotateY(Math.PI / 4), std(0x1a2026, { metalness: 0.5 }), x, BASE + h + 9, z, false);
  if (R() < 0.25) glow(scene, 0xff3030, 3, x, BASE + h + 2, z, 0.8);
}
// крыша героя
const roofM = std(0x1a1e22, { roughness: 0.25, metalness: 0.55 });
box(scene, 34, 1, 30, roofM, 0, -0.5, 4);
const parM = std(0x3a3e42, { roughness: 0.8 });
box(scene, 34, 1.2, 0.8, parM, 0, 0.6, -10.6);
box(scene, 0.8, 1.2, 30, parM, -16.6, 0.6, 4); box(scene, 0.8, 1.2, 30, parM, 16.6, 0.6, 4);
box(scene, 34, 120, 30, std(0x101418, { roughness: 0.9 }), 0, -61, 4, false);
// тёплый фонарь у выхода на крышу и холодный заполняющий свет на парапет
const lamp = new THREE.PointLight(0xffb066, 30, 18, 1.6); lamp.position.set(6, 3.2, -4); scene.add(lamp);
glow(scene, 0xffc080, 1.6, 6, 3.2, -4, 0.85);
box(scene, 3, 3, 3, std(0x2a2e33, { roughness: 0.8 }), 8, 1.5, -2);
const fillS = new THREE.SpotLight(0xa8c8ff, 120, 30, 0.5, 0.6, 1.4); fillS.position.set(3, 12, 2); fillS.target.position.set(0, 1, -10); scene.add(fillS, fillS.target);
// водонапорная башня
const tankM = std(0x4a3a2c, { roughness: 0.85 });
add(scene, new THREE.CylinderGeometry(2.2, 2.2, 4, 20), tankM, -9, 6, 2);
add(scene, new THREE.ConeGeometry(2.5, 1.6, 20), std(0x2a2a2a), -9, 8.8, 2);
for (const [dx, dz] of [[-1.5, -1.5], [1.5, -1.5], [-1.5, 1.5], [1.5, 1.5]]) add(scene, new THREE.CylinderGeometry(0.12, 0.12, 4, 6), std(0x222222), -9 + dx, 2, 2 + dz);
// горгулья на углу парапета
const garM = std(0x55585a, { roughness: 0.9, flatShading: true });
const gar = new THREE.Group(); gar.position.set(-6, 1.2, -10.6); scene.add(gar);
add(gar, new THREE.IcosahedronGeometry(0.55, 0), garM, 0, 0.5, 0); add(gar, new THREE.IcosahedronGeometry(0.35, 0), garM, 0, 1.15, -0.25);
for (const s of [-1, 1]) { const wng = add(gar, new THREE.ConeGeometry(0.4, 1.1, 3), garM, s * 0.55, 0.9, 0.2); wng.rotation.z = s * 1.0; }
// антенна с огоньком
add(scene, new THREE.CylinderGeometry(0.05, 0.08, 7, 6), std(0x333333, { metalness: 0.7 }), 10, 3.5, 6);
const beacon = glow(scene, 0xff2a2a, 1.4, 10, 7.1, 6, 0.9);

// облака и бэт-сигнал
const cloudTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = 'rgba(0,0,0,0)'; g.clearRect(0, 0, w, h);
  for (let i = 0; i < 220; i++) { const x = R() * w, y = R() * h, r = 30 + R() * 90; const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, `rgba(70,90,105,${0.10 + R() * 0.12})`); gr.addColorStop(1, 'rgba(70,90,105,0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r); }
}, [2, 2]);
const clouds = add(scene, new THREE.PlaneGeometry(1400, 1400).rotateX(Math.PI / 2), new THREE.MeshBasicMaterial({ map: cloudTex, transparent: true, depthWrite: false, side: THREE.DoubleSide, fog: false }), 0, 92, -200, false);
const SIG = V(-14, 90, -185);
const batTex = ctex(512, 512, (g, w, h) => {
  const c = w / 2; const gr = g.createRadialGradient(c, c, 0, c, c, c);
  gr.addColorStop(0, 'rgba(255,236,150,0.95)'); gr.addColorStop(0.62, 'rgba(255,220,120,0.85)'); gr.addColorStop(0.72, 'rgba(255,210,110,0.25)'); gr.addColorStop(1, 'rgba(255,210,110,0)');
  g.fillStyle = gr; g.beginPath(); g.ellipse(c, c, c, c * 0.62, 0, 0, Math.PI * 2); g.fill();
  // силуэт летучей мыши (собственная форма)
  g.fillStyle = 'rgba(10,10,12,0.95)'; g.beginPath();
  const pts = [[0, -18], [10, -30], [14, -14], [40, -40], [70, -30], [110, -36], [92, -16], [100, 6], [70, 0], [50, 22], [26, 10], [12, 30], [0, 16]];
  g.moveTo(c, c + pts[0][1] * 1.2);
  for (const [x, y] of pts) g.lineTo(c + x * 1.5, c + y * 1.5);
  for (let k = pts.length - 1; k >= 0; k--) g.lineTo(c - pts[k][0] * 1.5, c + pts[k][1] * 1.5);
  g.fill();
});
const bat = add(scene, new THREE.PlaneGeometry(70, 70), new THREE.MeshBasicMaterial({ map: batTex, transparent: true, depthWrite: false, fog: false, side: THREE.DoubleSide }), SIG.x, SIG.y - 1, SIG.z, false);
bat.rotation.x = Math.PI / 2 - 0.5;
const SRC = V(-60, 8, -90);
const beamGeo = new THREE.CylinderGeometry(15, 1.2, 1, 32, 1, true); beamGeo.translate(0, 0.5, 0);
const beamTex = ctex(16, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(255,240,190,0.04)'); gr.addColorStop(1, 'rgba(255,240,190,0.35)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
const beam = new THREE.Mesh(beamGeo, new THREE.MeshBasicMaterial({ map: beamTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }));
beam.position.copy(SRC); const dirB = SIG.clone().sub(SRC); beam.scale.set(1, dirB.length(), 1);
beam.quaternion.setFromUnitVectors(V(0, 1, 0), dirB.clone().normalize()); scene.add(beam);
glow(scene, 0xfff0c0, 10, SRC.x, SRC.y, SRC.z, 0.9);

// дождь
const RN = 2600; const rainGeo = new THREE.BufferGeometry(); const rp = new Float32Array(RN * 6); rainGeo.setAttribute('position', new THREE.BufferAttribute(rp, 3));
const RAIN = []; for (let i = 0; i < RN; i++) RAIN.push([(R() - 0.5) * 40, R() * 30, (R() - 0.5) * 40, 18 + R() * 8]);
const rain = new THREE.LineSegments(rainGeo, new THREE.LineBasicMaterial({ color: 0xaac4d8, transparent: true, opacity: 0.35, fog: false })); rain.frustumCulled = false; scene.add(rain);
function updateRain(t, cam) {
  for (let i = 0; i < RN; i++) {
    const [x, y0, z, v] = RAIN[i]; const y = ((y0 - t * v) % 30 + 30) % 30 - 6;
    const X = cam.x + x, Z = cam.z + z - 8, Y = cam.y + y;
    rp.set([X, Y, Z, X + 0.05, Y + 0.55, Z], i * 6);
  }
  rainGeo.attributes.position.needsUpdate = true;
}
const STRIKES = [41.9, 45.3, 47.6];

// ---------- маска и камера ----------
const mask = makeMask(scene, { blob: true });
const MP = V(0, 2.75, -10.4);
const camPos = track([
  [40.55, V(1.5, 1.4, 4.5)], [42.2, V(2.2, 1.9, 1.5)], [45.5, V(-2.0, 2.3, -3.0)], [47.9, V(-0.6, 2.6, -5.2)],
  [48.35, V(-1.5, 6, -9)], [48.95, V(-8, 30, -40)],
]);
const camLook = track([
  [40.55, SIG.clone()], [41.6, V(-4, 40, -60)], [42.2, MP.clone(), 'stop'], [45.5, MP.clone()], [47.9, MP.clone(), 'stop'],
  [48.35, V(-10, 60, -80)], [48.95, SIG.clone()],
]);
const RG = rig(camera, camPos, camLook, t => 58 + 6 * smooth((t - 48.3) / 0.5));

function setState(t) {
  RG.set(t);
  updateRain(t, camera.position);
  let f = 0; for (const s of STRIKES) { const a = t - s; if (a > 0 && a < 0.5) f = Math.max(f, Math.exp(-a * 9) * (0.6 + 0.4 * Math.sin(a * 90))); }
  lightning.intensity = 6 * f; hemi.intensity = 0.45 + 1.2 * f;
  sky.material.uniforms.mid.value.setRGB(0.086 + 0.3 * f, 0.133 + 0.32 * f, 0.165 + 0.36 * f);
  beacon.material.opacity = 0.9 * (Math.sin(t * 5) > 0 ? 1 : 0.15);
  clouds.material.map.offset.set(t * 0.003, t * 0.001);
  const mp = MP.clone(); mp.y += Math.sin(t * 1.2) * 0.04;
  mask.pose(camera, mp, 2.4, 1, Math.sin(t * 0.6) * 0.08, 1.2);
}

export default {
  name: 'gotham', scene, camera,
  async prepare(t) { await mask.load('dark-knight', t); },
  set: setState,
  speed: t => RG.speed(t),
};
