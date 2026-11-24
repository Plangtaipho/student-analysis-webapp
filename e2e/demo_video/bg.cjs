// Background for the phone scene of the demo clip (text drawn by Chromium so Thai renders correctly).
const { chromium } = require("playwright");
const path = require("path");
const BASE = process.env.BASE_URL || "http://localhost:8079";
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
    @font-face{font-family:Plex;src:url(${BASE}/static/fonts/IBMPlexSansThaiLooped-SemiBold.ttf)}
    @font-face{font-family:PlexR;src:url(${BASE}/static/fonts/IBMPlexSansThaiLooped-Regular.ttf)}
    body{margin:0;width:1280px;height:720px;background:#f4f1ea;font-family:Plex,sans-serif;position:relative;overflow:hidden}
    .copy{position:absolute;left:96px;top:210px;width:600px;color:#15315b}
    .n{display:inline-grid;place-items:center;width:64px;height:64px;border-radius:50%;background:#f59e0b;font-size:36px;margin-bottom:22px}
    h1{font-size:46px;line-height:1.3;margin:0 0 18px}
    p{font-family:PlexR,sans-serif;font-size:24px;line-height:1.6;color:#475569;margin:0}
    .phone{position:absolute;left:778px;top:26px;width:381px;height:668px;border-radius:38px;background:#111827;box-shadow:0 24px 50px rgba(21,49,91,.25)}
  </style></head><body>
    <div class="copy"><div class="n">2</div><h1>นักเรียนสแกน QR<br>กรอกเองบนมือถือ</h1>
    <p>ไม่ต้องสมัคร ไม่ต้องโหลดแอป<br>ส่งแล้วได้รหัสไว้แก้คำตอบภายหลัง</p></div>
    <div class="phone"></div></body></html>`);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: path.join(__dirname, "out", "bg.png") });
  await b.close();
})();
