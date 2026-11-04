// Монтаж 3D-прохода: какая локация видна в момент t, скрещивание на переходах, смаз движения.
// Окна согласованы с timeline.py (TRANSITIONS) — одни времена для картинки и звука.
import { renderer, W, H, smooth } from './common.js';
import room from './loc_room.js';
import london from './loc_london.js';
import madrid from './loc_madrid.js';
import bronx from './loc_bronx.js';
import gotham from './loc_gotham.js';
import stage from './loc_stage.js';

const SHOTS = [
  { loc: room, t0: -1, t1: 15.52 },
  { loc: london, t0: 15.32, t1: 24.55 },
  { loc: madrid, t0: 24.35, t1: 32.65 },
  { loc: bronx, t0: 32.45, t1: 40.75 },
  { loc: gotham, t0: 40.55, t1: 48.95 },
  { loc: stage, t0: 48.75, t1: 999 },
];

function canvas() { const c = document.createElement('canvas'); c.width = W; c.height = H; return [c, c.getContext('2d')]; }
const [outC, outX] = canvas();
const [tmpC, tmpX] = canvas();

async function renderShot(loc, t, ctx) {
  await loc.prepare(t);
  const v = loc.speed(t);
  const N = v < 1.5 ? 1 : Math.min(12, Math.ceil(v / 1.6));
  const shutter = 0.5 / 60;
  for (let k = 0; k < N; k++) {
    const tk = N === 1 ? t : t + ((k + 0.5) / N - 0.5) * shutter;
    loc.set(tk); renderer.render(loc.scene, loc.camera);
    ctx.globalAlpha = 1 / (k + 1); ctx.drawImage(renderer.domElement, 0, 0);
  }
  ctx.globalAlpha = 1;
  return N;
}

window.shotsAt = t => SHOTS.filter(s => t >= s.t0 && t < s.t1).map(s => s.loc.name);
window.renderAt = async (t) => {
  const act = SHOTS.filter(s => t >= s.t0 && t < s.t1);
  await renderShot(act[0].loc, t, outX);
  if (act.length > 1) {
    const w = smooth((t - act[1].t0) / (act[0].t1 - act[1].t0));
    await renderShot(act[1].loc, t, tmpX);
    outX.globalAlpha = w; outX.drawImage(tmpC, 0, 0); outX.globalAlpha = 1;
  }
  return outC.toDataURL('image/png');
};
window.READY = true;
