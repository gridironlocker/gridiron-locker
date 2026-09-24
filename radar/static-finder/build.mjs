#!/usr/bin/env node
// Builds the code-protected static Customer Finder into site/private/customer-finder/index.html
//
//   CF_CODE='your-code' node radar/static-finder/build.mjs
//
// The whole dashboard (HTML + JS + catalogue) is encrypted with AES-256-GCM using a key
// derived from the code (PBKDF2-SHA256, 600k iterations). The published file contains only
// ciphertext plus a small unlock screen. The code itself is never written anywhere.
// Honest limits: this is not server-side access control. Anyone can download the encrypted
// file and try to guess the code offline, so a longer code means stronger protection.
import fs from "fs";
import path from "path";
import crypto from "crypto";
import { fileURLToPath } from "url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const RADAR = path.resolve(HERE, "..");
const REPO = path.resolve(RADAR, "..");
// CF_OUT lets the test suite build into a temp directory instead of the committed page.
const OUT = process.env.CF_OUT || path.join(REPO, "site", "private", "customer-finder", "index.html");
const ITER = 600000;

const code = process.env.CF_CODE;
if (!code) { console.error("Set CF_CODE to the access code, e.g. CF_CODE='…' node radar/static-finder/build.mjs"); process.exit(1); }

// 1. bundle the pure engine modules (same code the server uses)
const strip = (s) => s.replace(/^import .*?;\s*$/gm, "").replace(/^export \{[^}]*\} from .*?;\s*$/gm, "").replace(/^export (?=(async )?function|const|let|class)/gm, "");
const lib = (f) => strip(fs.readFileSync(path.join(RADAR, "lib/customer-finder", f), "utf-8"));
const catalogue = JSON.parse(fs.readFileSync(path.join(REPO, "data/catalogue-live.json"), "utf-8")).products
  .filter((p) => p.site_published !== false)
  .map(({ slug, name, collection, url, price_usd, garment, theme }) => ({ slug, name, collection, url, price_usd, garment, theme }));
const engine = fs.readFileSync(path.join(HERE, "browser-engine.js"), "utf-8").replace("/*CATALOGUE*/[]", JSON.stringify(catalogue));
const bundle = ["teams.js", "classifier.js", "dedupe-core.js", "match.js", "responder.js"].map(lib).join("\n") + "\n" + engine;

// 1b. the "Free discovery" panel (assisted search, bookmarklet, paste box, Bluesky live radar)
const assistSrc = fs.readFileSync(path.join(HERE, "assist.html"), "utf-8");
const slice = (start, end) => {
  const a = assistSrc.indexOf(start), b = assistSrc.indexOf(end);
  if (a < 0 || b < 0 || b < a) throw new Error(`assist.html: missing ${start} / ${end}`);
  return assistSrc.slice(a + start.length, b).trim();
};
const assistMarkup = slice("<!--CF_ASSIST_MARKUP_START-->", "<!--CF_ASSIST_MARKUP_END-->");
const assistScript = slice("<!--CF_ASSIST_SCRIPT_START-->", "<!--CF_ASSIST_SCRIPT_END-->").replace(/<\/script/gi, "<\\/script");

// 2. adapt the server dashboard to run fully in the browser
let html = fs.readFileSync(path.join(RADAR, "public/customer-finder.html"), "utf-8");
const apiStart = html.indexOf("async function api(");
const apiEnd = html.indexOf("\n}\n", apiStart) + 3;
if (apiStart < 0 || apiEnd < 3) throw new Error("dashboard api() not found");
html = html.slice(0, apiStart) + "async function api(path, opts = {}) { return localApi(path, opts); }\n" + html.slice(apiEnd);
const swaps = [
  [/const me = await fetch\("\/radar\/api\/auth\/me"\)[^\n]*\n\s*\$\("who"\)\.textContent = me\.user \|\| "";/, `$("who").textContent = "Static build · data saved in this browser";`],
  [/\$\("logout"\)\.addEventListener\("click", async \(e\) => \{[^\n]*\}\);/, `$("logout").addEventListener("click", (e) => { e.preventDefault(); sessionStorage.removeItem("gl_cf_key"); location.reload(); });`],
  [`<a href="#" id="logout">Sign out</a>`, `<a href="#" id="exp">Export backup</a> · <label style="cursor:pointer;color:#F2B01E">Import<input type="file" id="imp" accept="application/json" hidden></label> · <a href="#" id="logout">Lock</a>`],
  [`<script>\nconst BASE`, `<script>\n${bundle.replace(/<\/script/gi, "<\\/script")}\n</script>\n<script>\nconst BASE`],
  [`(async () => {\n`, `$("exp").addEventListener("click", (e) => { e.preventDefault(); cfExport(); });\n$("imp").addEventListener("change", (e) => e.target.files[0] && cfImport(e.target.files[0]));\n(async () => {\n`],
  [`<p class="small" style="margin-top:20px">Privacy:`, `<p class="small" style="margin-top:20px">Static site build: the automatic search inside this page is <b>Lemmy</b> only — Reddit's keyless JSON and Bluesky's searchPosts now return 403 to a browser, so they were removed instead of faked; X and web-search APIs need secret keys and live only in the Radar server build. Use the <b>Free discovery</b> panel above: assisted searches in your own logged-in browser, the Send to Finder bookmarklet, the paste box and the Bluesky live radar. Leads are saved in this browser; use Export backup regularly.</p>\n  <p class="small">Privacy:`],
  // "rejected (no link)" is a real outcome of this build, so it belongs in the header line too
  [`Sellers/media/off-topic excluded: <b id="m-exc">0</b></div>`, `Sellers/media/off-topic excluded: <b id="m-exc">0</b> · Missing link rejected: <b id="m-rej">0</b></div>`],
  // 1c. the Free discovery panel, straight after the status banner
  [`<div id="banner" class="banner"></div>`, `<div id="banner" class="banner"></div>\n\n${assistMarkup}`],
  // 1d. its script, just before the end of the document
  [`</body>\n</html>`, `<script>\n${assistScript}\n</script>\n</body>\n</html>`],
];
for (const [a, b] of swaps) {
  const before = html; html = html.replace(a, b);
  if (html === before) throw new Error("template swap failed: " + String(a).slice(0, 60));
}
// the dashboard never fills #m-rej (the server build has no such count), so the panel does it
if (!assistScript.includes("m-rej")) throw new Error("assist script must paint #m-rej");

// 3. encrypt
const salt = crypto.randomBytes(16), iv = crypto.randomBytes(12);
const key = crypto.pbkdf2Sync(code, salt, ITER, 32, "sha256");
const c = crypto.createCipheriv("aes-256-gcm", key, iv);
const ct = Buffer.concat([c.update(html, "utf-8"), c.final(), c.getAuthTag()]);
const b64 = (b) => b.toString("base64");

// 4. unlock screen (no links in, noindex, nothing readable without the code)
const gate = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex">
<meta name="googlebot" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<title>Private</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0b0d;color:#e8eaed;font-family:Inter,system-ui,sans-serif;padding:20px}
.c{width:100%;max-width:380px;background:#111418;border:1px solid #22262d;border-radius:14px;padding:28px}
h1{font-size:1.1rem;margin:0 0 14px}input{width:100%;box-sizing:border-box;padding:12px;border-radius:10px;border:1px solid #2a3038;background:#0f1215;color:#e8eaed;font-size:1rem}
button{width:100%;margin-top:12px;padding:12px;border:0;border-radius:10px;background:#F2B01E;color:#0a0b0d;font-weight:800;font-size:1rem;cursor:pointer}
#e{color:#f87171;min-height:1.2em;margin-top:10px;font-size:.9rem}
</style>
</head>
<body>
<form class="c" id="f"><h1>🔒 Private area</h1><input id="p" type="password" autocomplete="current-password" placeholder="Access code" autofocus><button>Unlock</button><div id="e"></div></form>
<script>
const D={s:"${b64(salt)}",i:"${b64(iv)}",c:"${b64(ct)}",n:${ITER}};
const u=(s)=>Uint8Array.from(atob(s),(c)=>c.charCodeAt(0));
async function open(key){
  const pt=await crypto.subtle.decrypt({name:"AES-GCM",iv:u(D.i)},key,u(D.c));
  const h=new TextDecoder().decode(pt); document.open(); document.write(h); document.close();
}
async function derive(code){
  const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(code),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2",salt:u(D.s),iterations:D.n,hash:"SHA-256"},base,{name:"AES-GCM",length:256},true,["decrypt"]);
}
(async()=>{const k=sessionStorage.getItem("gl_cf_key");if(k){try{await open(await crypto.subtle.importKey("raw",u(k),"AES-GCM",true,["decrypt"]));return;}catch{sessionStorage.removeItem("gl_cf_key");}}})();
document.getElementById("f").addEventListener("submit",async(ev)=>{ev.preventDefault();const e=document.getElementById("e");e.textContent="Checking…";
  try{const key=await derive(document.getElementById("p").value);await crypto.subtle.decrypt({name:"AES-GCM",iv:u(D.i)},key,u(D.c));
    const raw=new Uint8Array(await crypto.subtle.exportKey("raw",key));sessionStorage.setItem("gl_cf_key",btoa(String.fromCharCode(...raw)));await open(key);}
  catch{e.textContent="Wrong code.";}});
</script>
</body>
</html>
`;
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, gate);
console.log(`Wrote ${path.relative(REPO, OUT)} (${(gate.length / 1024).toFixed(1)} KB, encrypted)`);
