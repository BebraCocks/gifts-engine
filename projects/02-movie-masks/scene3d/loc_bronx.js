// Локация 4: длинная уличная лестница между кирпичными домами (Бронкс / Готэм), золотой час.
// Маска Arthur Fool. Камера поднимается по лестнице с лёгким «танцующим» креном, в конце — рывок в небо.
import * as THREE from 'three';
import { rng, clamp01, smooth, lerp, V, ctex, std, add, box, glow, skyDome, track, makeMask, rig, newCamera } from './common.js';

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xc08a60, 0.016);
const camera = newCamera();
const R = rng(2019104);
skyDome(scene, 0x3a6a9a, 0xf0b47a, 0x4a3020);
glow(scene, 0xffd9a0, 120, 0, 40, -220, 0.6);

scene.add(new THREE.HemisphereLight(0xffd2a8, 0x3a2418, 0.75));
const sun = new THREE.DirectionalLight(0xffc488, 3.4);
sun.position.set(6, 30, -70); sun.target.position.set(0, 0, -10); scene.add(sun, sun.target);
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -25, right: 25, top: 30, bottom: -30, near: 1, far: 150 });
sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.03;

const brickTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#7a3a28'; g.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 12) for (let x = (y / 12) % 2 * 14; x < w; x += 28) { g.fillStyle = `rgb(${110 + R() * 40},${50 + R() * 20},${36 + R() * 14})`; g.fillRect(x + 1, y + 1, 26, 10); }
  for (let x = 30; x < w; x += 96) for (let y = 40; y < h; y += 120) {
    g.fillStyle = '#e8dccc'; g.fillRect(x - 4, y - 4, 48, 72);
    g.fillStyle = R() < 0.3 ? '#ffcf8a' : '#2a3442'; g.fillRect(x, y, 40, 64);
    g.fillStyle = '#e8dccc'; g.fillRect(x + 18, y, 4, 64); g.fillRect(x, y + 30, 40, 4);
  }
}, [2, 2]);
const concreteTex = ctex(256, 256, (g, w, h) => {
  g.fillStyle = '#9a948a'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 3000; i++) { const v = 120 + R() * 50; g.fillStyle = `rgba(${v},${v - 4},${v - 10},0.45)`; g.fillRect(R() * w, R() * h, 2, 2); }
}, [4, 1]);

// лестница: три марша и две площадки, вверх по -z
const stepM = std(0xffffff, { map: concreteTex, roughness: 0.9 });
const STEP_H = 0.18, STEP_D = 0.36, WIDTH = 6.2;
const flights = [[0, 0, 22], [22 * STEP_H, -22 * STEP_D - 2.4, 22], [44 * STEP_H, -44 * STEP_D - 4.8, 26]];
export function stairY(z) {          // высота поверхности лестницы под точкой z (для маски/камеры)
  let y = 0;
  for (const [y0, z0, n] of flights) { if (z <= z0) y = y0 + Math.min(n, Math.max(0, (z0 - z) / STEP_D)) * STEP_H; }
  return y;
}
{
  const geo = new THREE.BoxGeometry(WIDTH, STEP_H, STEP_D);
  const total = flights.reduce((s, f) => s + f[2], 0);
  const inst = new THREE.InstancedMesh(geo, stepM, total); inst.castShadow = true; inst.receiveShadow = true;
  const m = new THREE.Matrix4(); let i = 0;
  for (const [y0, z0, n] of flights) for (let k = 0; k < n; k++) { m.makeTranslation(0, y0 + (k + 0.5) * STEP_H, z0 - (k + 0.5) * STEP_D); inst.setMatrixAt(i++, m); }
  scene.add(inst);
  for (const [y0, z0, n] of flights) {
    // площадка в конце марша
    box(scene, WIDTH, 0.3, 2.4, stepM, 0, y0 + n * STEP_H - 0.15, z0 - n * STEP_D - 1.2);
    // массив под маршем
    const len = n * STEP_D; const sh = new THREE.Shape(); sh.moveTo(0, 0); sh.lineTo(len, n * STEP_H); sh.lineTo(len, -0.4); sh.lineTo(0, -0.4);
    const side = add(scene, new THREE.ExtrudeGeometry(sh, { depth: WIDTH, bevelEnabled: false }), stepM, -WIDTH / 2, y0, z0); side.rotation.y = Math.PI / 2; side.position.x = -WIDTH / 2; side.rotation.y = Math.PI / 2;
  }
  // перила: центральные и боковые
  const railM = std(0x2c3a2c, { metalness: 0.6, roughness: 0.4 });
  for (const x of [-WIDTH / 2 + 0.1, 0, WIDTH / 2 - 0.1]) for (const [y0, z0, n] of flights) {
    const len = Math.hypot(n * STEP_D, n * STEP_H); const ang = Math.atan2(n * STEP_H, n * STEP_D);
    const r = box(scene, 0.07, 0.07, len, railM, x, y0 + n * STEP_H / 2 + 1.0, z0 - n * STEP_D / 2); r.rotation.x = ang;
    for (let k = 0; k <= n; k += 4) box(scene, 0.05, 1.0, 0.05, railM, x, y0 + k * STEP_H + 0.5, z0 - k * STEP_D);
  }
}
// улица внизу и наверху
add(scene, new THREE.PlaneGeometry(200, 40).rotateX(-Math.PI / 2), std(0x3a3632, { roughness: 0.9 }), 0, 0, 18, false);
const TOPY = stairY(-60), TOPZ = -44 * STEP_D - 4.8 - 26 * STEP_D - 2.4;
box(scene, 200, 0.3, 40, std(0x5a5550, { roughness: 0.9 }), 0, TOPY - 0.15, TOPZ - 20, false);
// дома по бокам лестницы
const brickM = std(0xffffff, { map: brickTex, roughness: 0.9 });
for (const sx of [-1, 1]) {
  for (const [z, d, h] of [[2, 18, 26], [-16, 18, 30], [-34, 18, 28]]) {
    const b = box(scene, 14, h, d, brickM, sx * (WIDTH / 2 + 0.4 + 7), h / 2 - 2 + (z < -10 ? stairY(z) * 0.6 : 0), z);
    b.material = brickM;
    box(scene, 14.4, 0.6, d + 0.4, std(0x4a3a30), sx * (WIDTH / 2 + 0.4 + 7), h - 2 + (z < -10 ? stairY(z) * 0.6 : 0) + 0.3, z);
  }
  // пожарные лестницы на фасаде, обращённом к лестнице
  const fe = std(0x1c1c1c, { metalness: 0.7, roughness: 0.5 });
  for (const z of [4, -12, -28]) for (let lvl = 1; lvl < 6; lvl++) {
    const y = 2 + lvl * 3.6 + (z < -10 ? stairY(z) * 0.6 : 0);
    box(scene, 0.9, 0.08, 3.2, fe, sx * (WIDTH / 2 + 0.85), y, z);
    box(scene, 0.04, 0.9, 3.2, fe, sx * (WIDTH / 2 + 0.42), y + 0.45, z);
    const st = box(scene, 0.5, 0.05, 3.9, fe, sx * (WIDTH / 2 + 0.85), y + 1.8, z + (lvl % 2 ? 0.4 : -0.4)); st.rotation.x = (lvl % 2 ? 1 : -1) * 0.95;
  }
}
// дом напротив наверху и фонари
box(scene, 40, 30, 12, brickM, 0, TOPY + 15, TOPZ - 26);
for (const z of [6, -18, -38]) {
  const y = stairY(z);
  add(scene, new THREE.CylinderGeometry(0.08, 0.1, 4.4, 8), std(0x1e2a1e, { metalness: 0.6 }), WIDTH / 2 - 0.4, y + 2.2, z);
  glow(scene, 0xffe2b0, 1.4, WIDTH / 2 - 0.9, y + 4.3, z, 0.7);
}
// пыль в лучах
const dustGeo = new THREE.BufferGeometry(); const dn = 600; const dp = new Float32Array(dn * 3);
for (let i = 0; i < dn; i++) { dp[i * 3] = (R() - 0.5) * 7; dp[i * 3 + 1] = R() * 16; dp[i * 3 + 2] = 6 - R() * 40; }
dustGeo.setAttribute('position', new THREE.BufferAttribute(dp, 3));
const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0xffe0b0, size: 0.05, transparent: true, opacity: 0.55, depthWrite: false }));
scene.add(dust);

// ---------- маска и камера ----------
const mask = makeMask(scene, { blob: true });
const MZ = -17.5, MP = V(0, stairY(MZ) + 1.9, MZ);
const camPos = track([
  [32.45, V(0.2, 1.4, 9)], [34.5, V(-1.2, 2.1, 4.5)], [37.5, V(1.3, stairY(-6) + 1.7, -6)], [39.75, V(0.4, stairY(-10) + 1.6, -10.5)],
  [40.25, V(0.3, stairY(-11) + 2.6, -11.5)], [40.8, V(0.2, stairY(-12) + 7, -12.5)],
]);
const camLook = track([
  [32.45, V(0, 4, -20)], [34.5, MP.clone(), 'stop'], [37.5, MP.clone()], [39.75, MP.clone(), 'stop'], [40.25, MP.clone().add(V(0, 9, -6))], [40.8, V(0, 60, -40)],
]);
// лёгкий «танец» камеры, как спуск героя по лестнице, затихает к концу
const RG = rig(camera, camPos, camLook, t => 56 + 4 * smooth((t - 40.2) / 0.5), t => Math.sin((t - 32.45) * 2.1) * 0.035 * (1 - smooth((t - 39.0) / 1.0)));

function setState(t) {
  RG.set(t);
  dust.rotation.y = t * 0.01; dust.position.y = Math.sin(t * 0.3) * 0.3;
  const mp = MP.clone(); mp.y += Math.sin(t * 1.5) * 0.07;
  mask.pose(camera, mp, 2.6, 1, Math.sin(t * 1.1) * 0.14, stairY(MZ));
}

export default {
  name: 'bronx', scene, camera,
  async prepare(t) { await mask.load('arthur-fool', t); },
  set: setState,
  speed: t => RG.speed(t),
};
