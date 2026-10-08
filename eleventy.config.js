import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import Image from "@11ty/eleventy-img";

const SRC = "src";
const RASTER = /\.(jpe?g|png|webp|gif|avif)$/i;

/* ------------------------------------------------------------------ utilitaires */
const escapeHtml = (s = "") =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Fichier média local (src/media/...) correspondant à une URL /media/... */
const localMedia = (src) => (src && src.startsWith("/media/") ? path.join(SRC, decodeURI(src)) : null);

/** Placeholder affiché tant qu'un visuel n'a pas été récupéré (demande du client). */
function placeholder(src, alt, { ratio = "16 / 9", className = "" } = {}) {
  const name = src ? path.basename(src) : "visuel manquant";
  return `<span class="media-placeholder ${className}" style="--ratio:${ratio}" role="img" aria-label="${escapeHtml(alt || "Visuel à venir")}"><span class="media-placeholder__label">Visuel à venir<small>${escapeHtml(name)}</small></span></span>`;
}

/**
 * {% image src, alt, sizes, className, ratio, loading %}
 * Shortcode SYNCHRONE : il écrit un marqueur <img data-img …> que la transformation
 * « responsiveImages » remplace ensuite (images AVIF/WebP/JPEG via eleventy-img,
 * SVG tel quel, placeholder si le fichier n'est pas encore dans src/media).
 * Un shortcode asynchrone ne fonctionne pas dans les {% if %} / {% for %} Nunjucks.
 */
function imageMarker(src, alt = "", sizes = "100vw", className = "", ratio = "", loading = "lazy", widths = "") {
  const attrs = { "data-img": "", src: src || "", alt: alt || "", sizes, class: className, "data-ratio": ratio, loading, "data-widths": widths };
  return "<img " + Object.entries(attrs).map(([k, v]) => (v === "" && k === "data-img" ? k : `${k}="${escapeHtml(v ?? "")}"`)).join(" ") + ">";
}
/** Variante : n'affiche rien si src est vide (image facultative). */
const imageMarkerOptional = (src, ...rest) => (src ? imageMarker(src, ...rest) : "");

const attr = (tag, name) => {
  const m = tag.match(new RegExp(`\\s${name}="([^"]*)"`));
  return m ? m[1].replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&") : "";
};

async function renderImage(src, alt, sizes, className, ratio, loading, widths = "") {
  if (!src) return placeholder(src, alt, { ratio: ratio || "16 / 9", className });
  const file = localMedia(src);
  if (!file || !fs.existsSync(file)) return placeholder(src, alt, { ratio: ratio || "16 / 9", className });
  const style = ratio ? ` style="aspect-ratio:${ratio}"` : "";
  if (!RASTER.test(file)) {
    return `<img src="${encodeURI(src)}" alt="${escapeHtml(alt)}"${className ? ` class="${className}"` : ""} loading="${loading}" decoding="async"${style}>`;
  }
  // Petites images (logos…) : largeurs dédiées, sans AVIF ; sinon jeu complet pour les visuels
  const custom = String(widths || "").split(",").map((w) => parseInt(w, 10)).filter(Boolean);
  const metadata = await Image(file, {
    widths: custom.length ? custom : [480, 800, 1200, 1800, 2400],
    formats: custom.length ? ["webp", "auto"] : ["avif", "webp", "auto"],
    outputDir: "_site/img/",
    urlPath: "/img/",
    sharpAvifOptions: { quality: 55, effort: 2 },
    sharpWebpOptions: { quality: 78 },
    sharpJpegOptions: { quality: 80, mozjpeg: true, progressive: true },
    filenameFormat: (id, srcPath, width, format) => `${path.parse(srcPath).name}-${id.slice(0, 6)}-${width}.${format}`,
  });
  return Image.generateHTML(metadata, {
    alt,
    sizes: sizes || "100vw",
    ...(className ? { class: className } : {}),
    loading: loading || "lazy",
    decoding: "async",
    ...(ratio ? { style: `aspect-ratio:${ratio}` } : {}),
    ...(loading === "eager" && !custom.length ? { fetchpriority: "high" } : {}),
  });
}

/** Transformation HTML : remplace les marqueurs <img data-img …> par les images finales. */
async function responsiveImages(content) {
  if (!this.page.outputPath || !this.page.outputPath.endsWith(".html") || !content.includes("data-img")) return content;
  const tags = [...new Set(content.match(/<img data-img [^>]*>/g) || [])];
  const rendered = await Promise.all(tags.map((t) =>
    renderImage(attr(t, "src"), attr(t, "alt"), attr(t, "sizes"), attr(t, "class"), attr(t, "data-ratio"), attr(t, "loading") || "lazy", attr(t, "data-widths"))));
  tags.forEach((t, i) => { content = content.split(t).join(rendered[i]); });
  return content;
}

/** URL absolue d'une image de partage (og:image) : version JPEG 1200 px générée. */
async function shareImage(src, siteUrl) {
  const file = localMedia(src);
  if (!file || !fs.existsSync(file) || !RASTER.test(file)) return src ? new URL(encodeURI(src), siteUrl).href : "";
  const md = await Image(file, {
    widths: [1200],
    formats: ["jpeg"],
    outputDir: "_site/img/",
    urlPath: "/img/",
    sharpJpegOptions: { quality: 82, mozjpeg: true },
    filenameFormat: (id, srcPath, width, format) => `${path.parse(srcPath).name}-${id.slice(0, 6)}-${width}.${format}`,
  });
  return new URL(md.jpeg[0].url, siteUrl).href;
}

/** "nos dernières *réalisations*" -> "nos dernières <em class="accent">réalisations</em>" */
function accent(s = "") {
  return escapeHtml(s).replace(/\*([^*]+)\*/g, '<em class="accent">$1</em>');
}

const vimeoId = (url = "") => (String(url).match(/(?:vimeo\.com\/(?:video\/)?|playback\/)(\d{6,})/) || [])[1] || null;

/* ------------------------------------------------------------------ configuration */
export default function (eleventyConfig) {
  eleventyConfig.addDataExtension("yml,yaml", (contents) => yaml.load(contents));

  // Fichiers servis tels quels
  eleventyConfig.addPassthroughCopy({ "src/media": "media" });
  eleventyConfig.addPassthroughCopy({ "src/assets": "assets" });
  eleventyConfig.addPassthroughCopy({ "src/static": "/" });
  eleventyConfig.addPassthroughCopy({
    "node_modules/@fontsource-variable/montserrat/files/montserrat-latin-wght-normal.woff2": "assets/fonts/montserrat-latin-wght-normal.woff2",
    "node_modules/@fontsource-variable/montserrat/files/montserrat-latin-ext-wght-normal.woff2": "assets/fonts/montserrat-latin-ext-wght-normal.woff2",
    "node_modules/@fontsource-variable/montserrat/files/montserrat-latin-wght-italic.woff2": "assets/fonts/montserrat-latin-wght-italic.woff2",
  });
  eleventyConfig.addWatchTarget("src/assets/");

  /* ---------------- collections */
  const byDateDesc = (a, b) => new Date(b.data.date) - new Date(a.data.date);
  const published = (item) => item.data.published !== false;

  eleventyConfig.addCollection("projets", (api) =>
    api.getFilteredByGlob("src/content/projets/*.md").filter(published).sort(byDateDesc));
  eleventyConfig.addCollection("actualites", (api) =>
    api.getFilteredByGlob("src/content/actualites/*.md").filter(published).sort(byDateDesc));
  eleventyConfig.addCollection("expertises", (api) =>
    api.getFilteredByGlob("src/content/expertises/*.md").sort((a, b) => (a.data.order || 0) - (b.data.order || 0)));
  eleventyConfig.addCollection("equipe", (api) =>
    api.getFilteredByGlob("src/content/equipe/*.md").filter(published).sort((a, b) => (a.data.order || 0) - (b.data.order || 0)));
  eleventyConfig.addCollection("offres", (api) =>
    api.getFilteredByGlob("src/content/offres/*.md").filter(published).sort(byDateDesc));
  eleventyConfig.addCollection("toutesOffres", (api) => api.getFilteredByGlob("src/content/offres/*.md"));
  // Pages indexables pour le sitemap
  eleventyConfig.addCollection("sitemap", (api) =>
    api.getAll().filter((p) => p.url && !p.data.noindex && published(p) && !/\.(xml|txt|php|htaccess)$/.test(p.url) && !p.url.endsWith(".html")));

  /* ---------------- shortcodes & filtres */
  eleventyConfig.addShortcode("image", imageMarker);
  eleventyConfig.addShortcode("imageOptional", imageMarkerOptional);
  eleventyConfig.addTransform("responsiveImages", responsiveImages);
  eleventyConfig.addAsyncFilter("shareImage", shareImage);
  eleventyConfig.addFilter("accent", accent);
  eleventyConfig.addFilter("vimeoId", vimeoId);
  eleventyConfig.addFilter("youtubeId", (url = "") => (String(url).match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([\w-]{11})/) || [])[1] || "");
  eleventyConfig.addFilter("mediaExists", (src) => {
    const f = localMedia(src);
    return !!(f && fs.existsSync(f));
  });
  eleventyConfig.addFilter("absoluteUrl", (url, base) => (url ? new URL(url, base).href : base));
  eleventyConfig.addFilter("bySlug", (items = [], slug) => items.find((i) => i.data.slug === slug));
  eleventyConfig.addFilter("bySlugs", (items = [], slugs = []) =>
    (slugs || []).map((s) => items.find((i) => i.data.slug === s)).filter(Boolean));
  eleventyConfig.addFilter("withExpertise", (items = [], slug) => items.filter((i) => (i.data.expertises || []).includes(slug)));
  eleventyConfig.addFilter("without", (items = [], url) => items.filter((i) => i.url !== url));
  eleventyConfig.addFilter("limit", (arr = [], n) => arr.slice(0, n));
  eleventyConfig.addFilter("dateFr", (d) => {
    const date = new Date(d);
    if (Number.isNaN(date.getTime())) return "";
    return `${String(date.getDate()).padStart(2, "0")}.${String(date.getMonth() + 1).padStart(2, "0")}.${date.getFullYear()}`;
  });
  eleventyConfig.addFilter("isoDate", (d) => {
    const date = new Date(d);
    return Number.isNaN(date.getTime()) ? "" : date.toISOString();
  });
  eleventyConfig.addFilter("stripTags", (s = "") => String(s).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim());
  eleventyConfig.addFilter("truncate", (s = "", n = 160) => (s.length > n ? s.slice(0, n - 1).replace(/\s+\S*$/, "") + "…" : s));
  eleventyConfig.addFilter("json", (v) => JSON.stringify(v));
  eleventyConfig.addFilter("year", () => new Date().getFullYear());
  // « SANDRA DE GRUTTOLA » / « Jérémy Dalbec » -> « Sandra DE GRUTTOLA » / « Jérémy DALBEC »
  eleventyConfig.addFilter("personName", (name = "") => {
    const [first, ...rest] = String(name).trim().split(/\s+/);
    const cap = (w) => w.split("-").map((p) => p.charAt(0).toLocaleUpperCase("fr") + p.slice(1).toLocaleLowerCase("fr")).join("-");
    return [cap(first), ...rest.map((w) => w.toLocaleUpperCase("fr"))].join(" ");
  });
  eleventyConfig.addFilter("findCategory", (cats = [], slug) => cats.find((c) => c.slug === slug));
  // Titre SEO comme WordPress : « Titre SEO | Nom du site », ou le nom du site seul
  eleventyConfig.addFilter("seoTitle", (seo, site) => (seo && seo.title ? `${seo.title} | ${site.title}` : site.title));

  eleventyConfig.addGlobalData("version", Date.now().toString(36));

  return {
    dir: { input: SRC, includes: "_includes", data: "_data", output: "_site" },
    templateFormats: ["njk", "md", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
  };
}
