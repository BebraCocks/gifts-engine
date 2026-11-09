// Рендер 3D-прохода в PNG: node render_scene.js <outDir> <from> <to> [--frames a,b,c] [--jobs N]
// Кадры — функция времени i/60. Маски берутся из ../build/masks (готовит prep_masks.py).
// 2026-11-09: несколько браузеров параллельно (--jobs или VIZ_3D_JOBS, по умолчанию — см. defaultJobs), кадры
// раздаются из общей очереди, поэтому тяжёлые кадры переходов не скапливаются у одного браузера. Каждые 10 % —
// строка PROGRESS с оставшимся временем. Готовые кадры пропускаются (--force — пересчитать), так что прерванный
// рендер можно продолжить. Каждый кадр зависит только от t, порядок и браузер на пиксели не влияют.
const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = __dirname;
const MASKS = path.join(ROOT, '..', 'build', 'masks');
const THREE_DIR = path.join(ROOT, 'node_modules', 'three', 'build');
const FPS = 60;

function fileFor(p) {
  if (p === '/' || p === '/index.html') return path.join(ROOT, 'index.html');
  if (p.startsWith('/three/')) return path.join(THREE_DIR, p.slice(7));
  if (p.startsWith('/masks/')) return path.join(MASKS, p.slice(7));
  return path.join(ROOT, p.slice(1));
}

function mmss(s) { s = Math.max(0, Math.round(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }

// SwiftShader (3D на процессоре) сам занимает несколько ядер, поэтому браузеров меньше, чем ядер: ~1 на 2 ядра,
// и не больше, чем помещается в 90 % RAM (~0,6 ГБ на браузер).
function defaultJobs() {
  if (process.env.VIZ_3D_JOBS) return Math.max(1, +process.env.VIZ_3D_JOBS);
  const byCpu = Math.max(1, Math.round(os.cpus().length / 2));
  const byRam = Math.max(1, Math.floor((os.freemem() - 0.10 * os.totalmem()) / (600 * 2 ** 20)));
  return Math.min(byCpu, byRam);
}

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.log('[error]', e.message));
  await page.route('http://local/**', route => {
    const file = fileFor(new URL(route.request().url()).pathname);
    if (!fs.existsSync(file)) return route.fulfill({ status: 404, body: 'missing ' + file });
    const type = file.endsWith('.js') ? 'text/javascript' : file.endsWith('.png') ? 'image/png' : 'text/html';
    route.fulfill({ status: 200, contentType: type, body: fs.readFileSync(file) });
  });
  await page.goto('http://local/index.html');
  await page.waitForFunction(() => window.READY === true, null, { timeout: 180000 });
  return page;
}

(async () => {
  const args = process.argv.slice(2);
  const outDir = args[0];
  let list;
  const fi = args.indexOf('--frames');
  if (fi >= 0) list = args[fi + 1].split(',').map(Number);
  else { list = []; for (let i = +args[1]; i < +args[2]; i++) list.push(i); }
  fs.mkdirSync(outDir, { recursive: true });
  const name = i => path.join(outDir, `f${String(i).padStart(5, '0')}.png`);
  if (!args.includes('--force')) {
    const before = list.length;
    list = list.filter(i => !fs.existsSync(name(i)));
    if (before !== list.length) console.log(`skip ${before - list.length} frames already rendered (--force to redo)`);
  }
  const ji = args.indexOf('--jobs');
  const jobs = Math.max(1, Math.min(list.length || 1, ji >= 0 ? +args[ji + 1] : defaultJobs()));
  console.log(`${list.length} frames, ${jobs} browsers (of ${os.cpus().length} cores)`);

  const t0 = Date.now();
  let next = 0, done = 0, mark = 10;
  async function worker() {
    const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
    try {
      const page = await openPage(browser);
      while (next < list.length) {
        const i = list[next++];
        const data = await page.evaluate(t => window.renderAt(t), i / FPS);
        const tmp = name(i) + '.part';
        fs.writeFileSync(tmp, Buffer.from(data.split(',')[1], 'base64'));
        fs.renameSync(tmp, name(i));                 // a half-written frame never looks finished
        done++;
        const pct = 100 * done / list.length;
        if (pct + 1e-9 >= mark) {
          while (mark <= pct + 1e-9) mark += 10;
          const el = (Date.now() - t0) / 1000;
          const tail = done < list.length ? `осталось ~${mmss(el / done * (list.length - done))}` : 'кадры готовы';
          console.log(`PROGRESS ${mark - 10}% · 3D-кадры ${done}/${list.length} · прошло ${mmss(el)} · ${tail}`);
        }
      }
    } finally {
      await browser.close();
    }
  }
  await Promise.all(Array.from({ length: jobs }, worker));
  console.log(`done ${list.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s ` +
              `(${((Date.now() - t0) / 1000 / Math.max(1, list.length)).toFixed(2)} s/frame, ${jobs} browsers)`);
})();
