// Vérifie que chaque lien interne (href/src commençant par /) du site généré pointe vers un fichier existant.
import fs from "node:fs";
import path from "node:path";

const OUT = "_site";
const files = [];
const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => {
  const p = path.join(d, e.name);
  e.isDirectory() ? walk(p) : p.endsWith(".html") && files.push(p);
});
walk(OUT);

const exists = (url) => {
  const clean = decodeURI(url.split("#")[0].split("?")[0]);
  if (!clean || clean === "/") return true;
  const p = path.join(OUT, clean);
  return fs.existsSync(p) && (fs.statSync(p).isFile() || fs.existsSync(path.join(p, "index.html")));
};

const broken = new Map();
for (const f of files) {
  const html = fs.readFileSync(f, "utf8");
  for (const m of html.matchAll(/\s(?:href|src|poster)="(\/[^"]*)"/g)) {
    const url = m[1];
    if (url.startsWith("//") || url === "/contact.php") continue;
    if (!exists(url)) broken.set(url, (broken.get(url) || new Set()).add(f.replace(OUT, "")));
  }
  for (const m of html.matchAll(/\ssrcset="([^"]*)"/g)) {
    for (const part of m[1].split(",")) {
      const url = part.trim().split(/\s+/)[0];
      if (url.startsWith("/") && !exists(url)) broken.set(url, (broken.get(url) || new Set()).add(f.replace(OUT, "")));
    }
  }
}

// Les médias pas encore récupérés sont signalés sans faire échouer la construction.
const media = [...broken.keys()].filter((u) => u.startsWith("/media/"));
const other = [...broken.keys()].filter((u) => !u.startsWith("/media/"));
console.log(`${files.length} pages vérifiées.`);
if (media.length) console.log(`${media.length} média(s) référencé(s) mais absent(s) de src/media (affichés en placeholder) :\n  ` + media.slice(0, 30).join("\n  ") + (media.length > 30 ? "\n  …" : ""));
if (other.length) {
  console.error(`${other.length} lien(s) interne(s) cassé(s) :`);
  for (const u of other) console.error(`  ${u}  ←  ${[...broken.get(u)].slice(0, 3).join(", ")}`);
  process.exit(1);
}
console.log("Aucun lien interne cassé.");
