// Локация 6 (финал): театральная сцена, пять масок в ряд в лучах прожекторов, занавес закрывается.
import * as THREE from 'three';
import { rng, clamp01, smooth, easeOut, easeIn, lerp, V, ctex, std, add, box, glow, track, makeMask, rig, newCamera } from './common.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x050304);
scene.fog = new THREE.FogExp2(0x0a0506, 0.035);
const camera = newCamera();
const R = rng(52);

scene.add(new THREE.HemisphereLight(0x553038, 0x080405, 0.35));
const woodTex = ctex(512, 512, (g, w, h) => {
  g.fillStyle = '#3a2216'; g.fillRect(0, 0, w, h);
  for (let x = 0; x < w; x += 32) { g.fillStyle = `hsl(22,${35 + R() * 10}%,${14 + R() * 7}%)`; g.fillRect(x + 1, 0, 30, h); }
}, [6, 3]);
add(scene, new THREE.PlaneGeometry(24, 14).rotateX(-Math.PI / 2), std(0xffffff, { map: woodTex, roughness: 0.45, metalness: 0.1 }), 0, 0, -2, false);
box(scene, 24, 1.2, 0.3, std(0x2a1610), 0, -0.6, 5);
// бархат: складки через смещение вершин
const velvet = std(0x8a0e18, { roughness: 0.85 });
function curtain(w, h, x, z, folds) {
  const geo = new THREE.PlaneGeometry(w, h, folds * 8, 2); const a = geo.attributes.position.array;
  for (let i = 0; i < a.length; i += 3) a[i + 2] += Math.sin(a[i] / w * folds * Math.PI * 2) * 0.22;
  geo.computeVertexNormals();
  return add(scene, geo, velvet, x, h / 2, z, false);
}
curtain(24, 10, 0, -8, 18);
const leftC = curtain(7, 10, -8.5, 3.2, 6), rightC = curtain(7, 10, 8.5, 3.2, 6);
box(scene, 26, 2.2, 0.6, velvet, 0, 9.4, 3.4);
const goldM = std(0xc89a48, { metalness: 0.8, roughness: 0.35 });
box(scene, 26, 0.3, 0.7, goldM, 0, 8.2, 3.5); box(scene, 0.5, 10, 0.7, goldM, -12.3, 5, 3.5); box(scene, 0.5, 10, 0.7, goldM, 12.3, 5, 3.5);
// рампа
for (let x = -10; x <= 10; x += 1.25) glow(scene, 0xffc070, 0.7, x, 0.15, 4.6, 0.8);

// пять масок и прожекторы
const NAMES = ['ghostface', 'anonymous', 'bella-ciao', 'arthur-fool', 'dark-knight'];
const XS = [-2.6, -1.3, 0, 1.3, 2.6];
const masks = NAMES.map(() => makeMask(scene, { blob: true }));
const coneTex = ctex(16, 256, (g, w, h) => { const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(255,235,200,0.0)'); gr.addColorStop(1, 'rgba(255,235,200,0.22)'); g.fillStyle = gr; g.fillRect(0, 0, w, h); });
const cones = [], spots = [];
XS.forEach((x, k) => {
  const geo = new THREE.CylinderGeometry(0.08, 0.95, 9, 24, 1, true); geo.translate(0, -4.5, 0);
  const c = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: coneTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false }));
  c.position.set(x, 9.2, -0.4); scene.add(c); cones.push(c);
  const s = new THREE.SpotLight(0xffe2b8, 0, 14, 0.22, 0.5, 1.4); s.position.set(x, 9.2, -0.4); s.target.position.set(x, 0, -0.4); scene.add(s, s.target); spots.push(s);
});

const camPos = track([[48.75, V(0, 2.1, 1.2)], [50.2, V(0, 2.3, 9.6)], [52.4, V(0, 2.25, 10.6), 'stop']]);
const camLook = track([[48.75, V(0, 2.0, -0.4)], [50.0, V(0, 1.9, -0.4)], [52.4, V(0, 2.0, -0.4), 'stop']]);
const RG = rig(camera, camPos, camLook, t => lerp(64, 50, smooth((t - 48.75) / 1.6)));
const CLOSE0 = 51.4, CLOSE1 = 52.3;

function setState(t) {
  RG.set(t);
  XS.forEach((x, k) => {
    const on = smooth((t - 48.9 - k * 0.12) / 0.25);
    spots[k].intensity = 160 * on; cones[k].material.opacity = on;
    const mp = V(x, 1.95 + Math.sin(t * 1.3 + k) * 0.05, -0.4);
    masks[k].pose(camera, mp, 1.2 * (0.85 + 0.15 * easeOut(on)), 1, Math.sin(t * 0.8 + k) * 0.1, 0);
    masks[k].mesh.material.opacity = 0.25 + 0.75 * on;
  });
  // занавес закрывается к последнему слову
  const k = easeIn(smooth((t - CLOSE0) / (CLOSE1 - CLOSE0)));
  leftC.position.x = lerp(-8.5, -3.5, k); rightC.position.x = lerp(8.5, 3.5, k);
}

export default {
  name: 'stage', scene, camera,
  async prepare(t) { await Promise.all(NAMES.map((n, k) => masks[k].load(n, t + k * 0.37))); },
  set: setState,
  speed: t => RG.speed(t),
};
