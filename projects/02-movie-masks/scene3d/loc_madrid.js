// Локация 3: Мадрид на закате — неоклассический фасад с колоннадой, ступени, флаги, дождь купюр.
// Маска Bella Ciao. Вход: камера выходит из облака купюр; выход: порыв купюр закрывает кадр.
import * as THREE from 'three';
import { rng, clamp01, smooth, easeIn, easeOut, lerp, V, ctex, std, add, box, glow, skyDome, track, makeMask, rig, newCamera } from './common.js';

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x6a3a4a, 0.012);
const camera = newCamera();
const R = rng(2017052);
skyDome(scene, 0x2a2a6a, 0xf08a5a, 0x3a2030);
glow(scene, 0xffb070, 140, -120, 30, -300, 0.55);
glow(scene, 0xfff0c0, 30, -120, 30, -300, 0.9);

scene.add(new THREE.HemisphereLight(0xffb39a, 0x2a1820, 0.7));
const sun = new THREE.DirectionalLight(0xffb070, 3.2);
sun.position.set(-40, 18, 10); sun.target.position.set(0, 0, -20); scene.add(sun, sun.target);
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -45, right: 45, top: 40, bottom: -10, near: 1, far: 140 });
sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.03;

const plazaTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#9a8a78'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 32) for (let x = 0; x < w; x += 32) { g.fillStyle = `rgba(${120 + R() * 40},${100 + R() * 30},${80 + R() * 25},0.5)`; g.fillRect(x + 1, y + 1, 30, 30); }
}, [40, 40]);
const wallTex = ctex(512, 256, (g, w, h) => {
  g.fillStyle = '#e2d2bc'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 16) { g.fillStyle = 'rgba(120,95,70,0.18)'; g.fillRect(0, y, w, 1); }
  for (let x = 20; x < w; x += 64) for (let y = 40; y < h - 30; y += 100) {
    g.fillStyle = '#5a4030'; g.fillRect(x, y, 26, 56); g.fillStyle = 'rgba(255,190,120,0.7)'; g.fillRect(x + 3, y + 3, 20, 50);
    g.fillStyle = '#cdbb9f'; g.fillRect(x - 4, y - 8, 34, 6);
  }
}, [3, 1]);
const noteTex = ctex(256, 128, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#b2468a'); gr.addColorStop(1, '#6a3a9a');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.strokeStyle = 'rgba(255,255,255,0.5)'; g.lineWidth = 3; g.strokeRect(6, 6, w - 12, h - 12);
  g.fillStyle = 'rgba(255,255,255,0.85)'; g.font = 'bold 54px sans-serif'; g.fillText('500', 20, 76);
  g.beginPath(); g.arc(196, 64, 34, 0, Math.PI * 2); g.fillStyle = 'rgba(255,230,160,0.55)'; g.fill();
  for (let i = 0; i < 40; i++) { g.fillStyle = 'rgba(255,255,255,0.12)'; g.fillRect(R() * w, R() * h, 30, 1); }
});

// площадь и здание
add(scene, new THREE.PlaneGeometry(260, 260).rotateX(-Math.PI / 2), std(0xffffff, { map: plazaTex, roughness: 0.85 }), 0, 0, -40, false);
const wallM = std(0xffffff, { map: wallTex, roughness: 0.85 });
const stoneM = std(0xe8dcc8, { roughness: 0.8 });
box(scene, 70, 24, 14, wallM, 0, 12, -40);
box(scene, 72, 1.6, 15, stoneM, 0, 24.8, -40);
box(scene, 30, 4, 10, stoneM, 0, 25, -28);                       // антаблемент портика
const ped = new THREE.Shape(); ped.moveTo(-16, 0); ped.lineTo(16, 0); ped.lineTo(0, 7); ped.lineTo(-16, 0);
add(scene, new THREE.ExtrudeGeometry(ped, { depth: 9, bevelEnabled: false }), stoneM, 0, 27, -32.5);
for (let k = 0; k < 8; k++) {
  const x = -12.6 + k * 3.6;
  add(scene, new THREE.CylinderGeometry(0.85, 0.95, 16.5, 24), stoneM, x, 0.8 + 8.25 + 2.4, -24.5);
  box(scene, 2.2, 0.7, 2.2, stoneM, x, 3.6, -24.5);
}
for (let k = 0; k < 8; k++) box(scene, 34 - k * 0.6, 0.45, 1.0, stoneM, 0, 0.225 + k * 0.45, -15.5 - k * 1.0);
box(scene, 34, 3.6, 8, stoneM, 0, 1.8, -24.5);
// двери с тёплым светом
box(scene, 4, 7, 0.4, std(0x3a2416), 0, 7.1, -32.9);
glow(scene, 0xffb060, 9, 0, 8, -32, 0.45);
// флаги
const flagTex = ctex(128, 96, (g, w, h) => { g.fillStyle = '#c60b1e'; g.fillRect(0, 0, w, h); g.fillStyle = '#ffc400'; g.fillRect(0, h / 4, w, h / 2); });
const flags = [];
for (const x of [-30, 30]) {
  add(scene, new THREE.CylinderGeometry(0.12, 0.12, 12, 8), std(0x333333, { metalness: 0.6, roughness: 0.4 }), x, 31.5, -38);
  const geo = new THREE.PlaneGeometry(6, 4, 24, 4); const f = add(scene, geo, std(0xffffff, { map: flagTex, side: THREE.DoubleSide, roughness: 0.7 }), x + 3, 35.5, -38, true);
  flags.push({ f, base: geo.attributes.position.array.slice() });
}
// фонари на площади
for (const x of [-20, -10, 10, 20]) {
  add(scene, new THREE.CylinderGeometry(0.12, 0.16, 5, 8), std(0x222222, { metalness: 0.6 }), x, 2.5, -8);
  glow(scene, 0xffd08a, 2.2, x, 5.2, -8, 0.9);
}
// дальние дома
for (let k = 0; k < 24; k++) { const x = -150 + k * 13; const h = 14 + R() * 18; box(scene, 12, h, 10, std(0xc8a088), x + (Math.abs(x) < 40 ? 0 : 0), h / 2, -75 - R() * 20, false); }

// ---------- купюры ----------
const noteMat = new THREE.MeshStandardMaterial({ map: noteTex, side: THREE.DoubleSide, roughness: 0.7, emissive: 0x401030, emissiveIntensity: 0.25 });
const NOTES = [];
for (let i = 0; i < 300; i++) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.4), noteMat); m.castShadow = false; m.frustumCulled = false; scene.add(m);
  NOTES.push({ m, x: (R() - 0.5) * 36, z: -24 + R() * 32, y0: R() * 30, v: 1.2 + R() * 1.0, ph: R() * 6.28, wob: 0.6 + R(), curtain: i < 70, cx: (R() - 0.5) * 2.4, cy: (R() - 0.5) * 3.6, cd: 0.5 + R() * 1.4 });
}
const CAM0 = V(0, 8.5, 6);
function notes(t, cam) {
  for (const n of NOTES) {
    let p;
    if (n.curtain && t < 25.2) {
      // старт: камера внутри облака купюр, они разлетаются
      const k = easeOut(clamp01((t - 24.35) / 0.85));
      p = CAM0.clone().add(V(n.cx * (0.6 + 6 * k), n.cy * (0.5 + 4 * k), -1.0 - n.cd - 6 * k));
    } else if (n.curtain && t > 32.0) {
      // финал: порыв несёт купюры в камеру
      const k = easeIn(clamp01((t - 32.0 - n.ph * 0.02) / (0.45 * n.cd)));
      const start = V(n.cx * 4, 4 + n.cy * 1.5, -12);
      p = start.lerp(cam.clone().add(V(n.cx * 0.35, n.cy * 0.3, -0.5)), k);
    } else {
      const fall = ((t - 20) * n.v + n.y0) % 30;
      p = V(n.x + Math.sin(t * n.wob + n.ph) * 0.8, 30 - fall, n.z + Math.cos(t * 0.7 * n.wob + n.ph) * 0.6);
    }
    n.m.position.copy(p);
    n.m.rotation.set(t * 1.6 * n.wob + n.ph, t * 0.9 + n.ph, Math.sin(t * 2 + n.ph) * 0.8);
  }
}

// ---------- маска и камера ----------
const mask = makeMask(scene, { blob: true });
const MP = V(0, 4.4, -11.5);
const camPos = track([
  [24.35, CAM0.clone()], [25.9, V(-3.2, 5.6, 0.5)], [29.4, V(3.2, 4.6, -3.0)], [31.95, V(1.0, 4.4, -5.2)], [32.6, V(0.3, 4.4, -8.6)],
]);
const camLook = track([
  [24.35, V(0, 6.5, -12)], [25.9, V(0, 4.6, -12), 'stop'], [29.4, V(0, 4.4, -12)], [31.95, V(0, 4.4, -12), 'stop'], [32.6, V(0, 4.4, -16)],
]);
const RG = rig(camera, camPos, camLook, t => 56 + 6 * smooth((t - 32.1) / 0.45));

function setState(t) {
  RG.set(t);
  notes(t, camera.position);
  for (const { f, base } of flags) {
    const a = f.geometry.attributes.position.array;
    for (let i = 0; i < a.length; i += 3) { const u = (base[i] + 3) / 6; a[i + 2] = base[i + 2] + Math.sin(t * 4 + base[i] * 1.3) * 0.35 * u; a[i + 1] = base[i + 1] + Math.sin(t * 3 + base[i] * 0.9) * 0.08 * u; }
    f.geometry.attributes.position.needsUpdate = true; f.geometry.computeVertexNormals();
  }
  const mp = MP.clone(); mp.y += Math.sin(t * 1.3) * 0.08;
  mask.pose(camera, mp, 3.1, 1, Math.sin(t * 0.8) * 0.1, 0);
}

export default {
  name: 'madrid', scene, camera,
  async prepare(t) { await mask.load('bella-ciao', t); },
  set: setState,
  speed: t => RG.speed(t),
};
