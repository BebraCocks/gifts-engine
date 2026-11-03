// Общие средства 3D-прохода: рендерер, детерминированный случайный генератор, текстуры из кода,
// траектории (Эрмит с касательными Катмулла–Рома по времени), маска-карточка с тенью.
import * as THREE from 'three';

export const W = 1080, H = 1920;
export const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

export function rng(seed) {
  return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
export const clamp01 = x => Math.min(1, Math.max(0, x));
export const smooth = x => { x = clamp01(x); return x * x * (3 - 2 * x); };
export const easeIn = x => { x = clamp01(x); return x * x * x; };
export const easeOut = x => { x = clamp01(x); return 1 - Math.pow(1 - x, 3); };
export const lerp = (a, b, k) => a + (b - a) * k;
export const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function ctex(w, h, fn, rep = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  fn(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(rep[0], rep[1]); t.anisotropy = 8;
  return t;
}
export const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, metalness: 0, ...o });
export const basic = (color, o = {}) => new THREE.MeshBasicMaterial({ color, ...o });
export function add(parent, geo, mat, x, y, z, shadow = true) {
  const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z);
  m.castShadow = shadow; m.receiveShadow = true; parent.add(m); return m;
}
export const box = (parent, w, h, d, mat, x, y, z, s = true) => add(parent, new THREE.BoxGeometry(w, h, d), mat, x, y, z, s);

export const glowTex = ctex(128, 128, (g, w, h) => {
  const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,0.45)');
  gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
});
export function glow(parent, color, size, x, y, z, opacity = 0.7) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity, fog: false }));
  s.scale.set(size, size, 1); s.position.set(x, y, z); parent.add(s); return s;
}
export const shadowTex = ctex(128, 128, (g, w, h) => {
  const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
  gr.addColorStop(0, 'rgba(0,0,0,0.85)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
});

export function skyDome(scene, top, mid, bot, radius = 400) {
  const sky = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { top: { value: new THREE.Color(top) }, mid: { value: new THREE.Color(mid) }, bot: { value: new THREE.Color(bot) } },
    vertexShader: 'varying vec3 vp; void main(){ vp = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
    fragmentShader: 'uniform vec3 top; uniform vec3 mid; uniform vec3 bot; varying vec3 vp; void main(){ float h = normalize(vp).y; vec3 c = h>0.0 ? mix(mid, top, pow(h,0.55)) : mix(mid, bot, pow(-h,0.4)); gl_FragColor = vec4(c,1.0); }',
  }));
  scene.add(sky); return sky;
}
export function stars(scene, R, n = 900, r = 380, color = 0xdfe6ff) {
  const pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const a = R() * Math.PI * 2, e = 0.1 + R() * 1.35; pos[i * 3] = r * Math.cos(e) * Math.sin(a); pos[i * 3 + 1] = r * Math.sin(e); pos[i * 3 + 2] = r * Math.cos(e) * Math.cos(a); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const p = new THREE.Points(geo, new THREE.PointsMaterial({ color, size: 2.2, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.85 }));
  scene.add(p); return p;
}

// Траектория по ключам [t, Vector3, 'stop'?]; 'stop' — нулевая скорость в ключе.
export function track(keys) {
  return t => {
    const n = keys.length;
    if (t <= keys[0][0]) return keys[0][1].clone();
    if (t >= keys[n - 1][0]) return keys[n - 1][1].clone();
    let i = 0; while (keys[i + 1][0] < t) i++;
    const [t0, p0] = keys[i], [t1, p1] = keys[i + 1], dt = t1 - t0, u = (t - t0) / dt;
    const tan = j => { if (keys[j][2] === 'stop' || j === 0 || j === n - 1) return V(0, 0, 0); return keys[j + 1][1].clone().sub(keys[j - 1][1]).divideScalar(keys[j + 1][0] - keys[j - 1][0]); };
    const m0 = tan(i).multiplyScalar(dt), m1 = tan(i + 1).multiplyScalar(dt);
    const u2 = u * u, u3 = u2 * u;
    return p0.clone().multiplyScalar(2 * u3 - 3 * u2 + 1).add(m0.multiplyScalar(u3 - 2 * u2 + u))
      .add(p1.clone().multiplyScalar(-2 * u3 + 3 * u2)).add(m1.multiplyScalar(u3 - u2));
  };
}

// Кадры Lottie (60 fps, 180 кадров) готовит prep_masks.py. Фаза сдвигается, не пинг-понг.
const imgCache = new Map();
export function loadImg(url) {
  if (!imgCache.has(url)) imgCache.set(url, new Promise((res, rej) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error('missing ' + url)); im.src = url; }));
  if (imgCache.size > 96) imgCache.delete(imgCache.keys().next().value);
  return imgCache.get(url);
}
export const MASK_OFFSET = { 'ghostface': 0.9, 'anonymous': 0.0, 'bella-ciao': 0.0, 'arthur-fool': 0.0, 'dark-knight': 1.5 };
export function maskUrl(name, t) {
  const idx = Math.floor((t + (MASK_OFFSET[name] || 0)) * 60 + 1e-6) % 180;
  return `/masks/${name}/${String((idx + 180) % 180).padStart(3, '0')}.png`;
}

// Маска-карточка: всегда лицом к камере (как 2D-персонажи в 3D-мире), с пятном тени на земле.
export function makeMask(scene, opts = {}) {
  const tex = new THREE.Texture(); tex.colorSpace = THREE.SRGBColorSpace;
  const mat = new THREE.MeshBasicMaterial({ map: tex, transparent: true, side: THREE.DoubleSide, toneMapped: false, fog: false, depthWrite: false });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat); mesh.renderOrder = 10; scene.add(mesh);
  const blob = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false, opacity: 0.6 }));
  blob.visible = !!opts.blob; scene.add(blob);
  return {
    mesh, blob, tex, name: null,
    async load(name, t) { const im = await loadImg(maskUrl(name, t)); if (tex.image !== im) { tex.image = im; tex.needsUpdate = true; } this.name = name; },
    pose(camera, pos, size, flipX = 1, spin = 0, ground = 0) {
      mesh.position.copy(pos); mesh.scale.set(size * Math.max(0.001, flipX), size, 1);
      mesh.quaternion.copy(camera.quaternion); if (spin) mesh.rotateY(spin);
      if (blob.visible) { blob.position.set(pos.x, ground + 0.03, pos.z); const h = Math.max(0, pos.y - ground - size / 2); const bs = size * 1.05 / (1 + h * 0.25); blob.scale.set(bs, 1, bs * 0.55); blob.material.opacity = 0.6 / (1 + h * 0.3); }
    },
  };
}

// Камера-рамка: позиция + цель + крен + FOV как функции времени
export function rig(camera, pos, look, fov = () => 58, roll = () => 0) {
  return {
    camera,
    set(t) { camera.position.copy(pos(t)); camera.lookAt(look(t)); camera.rotation.z += roll(t); camera.fov = fov(t); camera.updateProjectionMatrix(); },
    speed(t) {
      const d = 1 / 60, a = pos(t - d / 2), b = pos(t + d / 2);
      const la = look(t - d / 2).sub(a).normalize(), lb = look(t + d / 2).sub(b).normalize();
      return a.distanceTo(b) / d + la.angleTo(lb) / d * 4.0;     // м/с + вклад поворота
    },
  };
}
export function newCamera() { return new THREE.PerspectiveCamera(58, W / H, 0.05, 900); }
