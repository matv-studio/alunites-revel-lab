#!/usr/bin/env node
// Optimise les médias récupérés de WordPress pour le dépôt du site.
//   source : _import/medias-originaux/AAAA/MM/fichier
//   cible  : src/media/AAAA/MM/fichier (même nom, même extension : les redirections 301 en dépendent)
// JPEG : 2560 px maximum, mozjpeg qualité 82, métadonnées retirées (orientation appliquée).
// PNG  : 2560 px maximum, compression sans perte maximale (palette si l'image le permet).
// SVG, PDF, autres : copiés tels quels.
// Usage : node _import/tools/optimize-media.mjs [dossierSource] [dossierCible]
import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const SRC = path.resolve(process.argv[2] || "_import/medias-originaux");
const OUT = path.resolve(process.argv[3] || "src/media");
const MAX = 2560;

const files = [];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
  const p = path.join(d, e.name);
  if (e.isDirectory()) walk(p);
  else if (!e.name.endsWith(".part")) files.push(p);
});
if (!fs.existsSync(SRC)) { console.error(`Dossier source introuvable : ${SRC}`); process.exit(1); }
walk(SRC);

let before = 0, after = 0, done = 0, skipped = 0;
for (const file of files) {
  const rel = path.relative(SRC, file);
  const dest = path.join(OUT, rel);
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  const size = fs.statSync(file).size;
  before += size;
  if (fs.existsSync(dest) && fs.statSync(dest).mtimeMs >= fs.statSync(file).mtimeMs) { after += fs.statSync(dest).size; skipped++; continue; }
  const ext = path.extname(file).toLowerCase();
  try {
    if (ext === ".jpg" || ext === ".jpeg") {
      const buf = await sharp(file).rotate().resize(MAX, MAX, { fit: "inside", withoutEnlargement: true }).jpeg({ quality: 82, mozjpeg: true, progressive: true }).toBuffer();
      fs.writeFileSync(dest, buf.length < size ? buf : fs.readFileSync(file));
    } else if (ext === ".png") {
      const img = sharp(file).rotate().resize(MAX, MAX, { fit: "inside", withoutEnlargement: true });
      const lossless = await img.clone().png({ compressionLevel: 9, adaptiveFiltering: true, effort: 10 }).toBuffer();
      fs.writeFileSync(dest, lossless.length < size ? lossless : fs.readFileSync(file));
    } else {
      fs.copyFileSync(file, dest);
    }
  } catch (err) {
    console.warn(`  copie brute (${err.message}) : ${rel}`);
    fs.copyFileSync(file, dest);
  }
  after += fs.statSync(dest).size;
  done++;
  if (done % 25 === 0) console.log(`  ${done + skipped}/${files.length}…`);
}
const mb = (n) => (n / 1e6).toFixed(1) + " Mo";
console.log(`${files.length} fichiers (${done} traités, ${skipped} déjà à jour) : ${mb(before)} → ${mb(after)}`);
