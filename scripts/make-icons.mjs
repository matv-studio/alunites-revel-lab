// Génère favicon.png, apple-touch-icon.png et l'image de partage par défaut à partir des SVG de la marque.
import sharp from "sharp";
import fs from "node:fs";

const fav = fs.readFileSync("src/assets/img/favicon.svg");
await sharp({ create: { width: 192, height: 192, channels: 4, background: "#16171B" } })
  .composite([{ input: await sharp(fav, { density: 600 }).resize(132, 132, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer(), gravity: "center" }])
  .png().toFile("src/static/favicon.png");
await sharp({ create: { width: 180, height: 180, channels: 4, background: "#ffffff" } })
  .composite([{ input: await sharp(fav, { density: 600 }).resize(124, 124, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } }).png().toBuffer(), gravity: "center" }])
  .png().toFile("src/static/apple-touch-icon.png");

// Image de partage 1200×630 : dégradé de la DA + logotype blanc
const W = 1200, H = 630;
const bg = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f1cb8"/><stop offset=".22" stop-color="#7c34c8"/><stop offset=".48" stop-color="#a13e90"/><stop offset=".72" stop-color="#e2575f"/><stop offset=".88" stop-color="#fe7042"/><stop offset="1" stop-color="#fe9d44"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#g)"/></svg>`);
const logo = await sharp(fs.readFileSync("src/assets/img/logo-alunites-blanc.svg"), { density: 300 }).resize(760).png().toBuffer();
await sharp(bg).composite([{ input: logo, gravity: "center" }]).jpeg({ quality: 88, mozjpeg: true }).toFile("src/assets/img/partage.jpg");
console.log("icônes générées");
