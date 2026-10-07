#!/usr/bin/env python3
"""Lit l'export WordPress (WXR) d'alunites.com et produit un modèle de contenu normalisé.

Sortie : _import/data/content.json et _import/data/media.json

Les champs ACF sont stockés à plat dans les postmeta (ex. blocks_2_texts_0_text) ;
ce script les reconstruit d'après le schéma des groupes de champs ACF du site.
"""
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WXR = ROOT / "wxr" / "export.xml"
OUT = ROOT / "data"

NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}

# Pages WordPress réellement servies par le site (les doublons sont des copies WPML non publiées en front).
LIVE_PAGE_IDS = {"home": "7", "agence": "204", "contact": "18", "mentions-legales": "47", "projets": "56", "actualites": "26"}


# --------------------------------------------------------------------------- PHP unserialize
def php_unserialize(s: str):
    """Désérialise le sous-ensemble PHP utilisé par WordPress/ACF (a, s, i, d, b, N)."""
    if s is None:
        return None
    data = s.encode("utf-8")
    pos = 0

    def read_until(ch: bytes) -> bytes:
        nonlocal pos
        end = data.index(ch, pos)
        out = data[pos:end]
        pos = end + 1
        return out

    def parse():
        nonlocal pos
        t = data[pos:pos + 1]
        pos += 2  # type + ':' (ou ';' pour N)
        if t == b"N":
            return None
        if t == b"i":
            return int(read_until(b";"))
        if t == b"d":
            return float(read_until(b";"))
        if t == b"b":
            return read_until(b";") == b"1"
        if t == b"s":
            n = int(read_until(b":"))
            pos += 1  # "
            val = data[pos:pos + n].decode("utf-8")
            pos += n + 2  # ";
            return val
        if t == b"a":
            n = int(read_until(b":"))
            pos += 1  # {
            out = {}
            for _ in range(n):
                k = parse()
                v = parse()
                out[k] = v
            pos += 1  # }
            if all(isinstance(k, int) for k in out) and list(out) == list(range(len(out))):
                return [out[i] for i in range(len(out))]
            return out
        raise ValueError(f"type PHP inconnu {t!r} à {pos}")

    try:
        return parse()
    except Exception:
        return s


def is_serialized(v: str | None) -> bool:
    return bool(v) and re.match(r"^(a|s|i|d|b):", v or "") is not None and v.rstrip().endswith((";", "}"))


# --------------------------------------------------------------------------- HTML
BLOCK_TAGS = r"(?:table|thead|tfoot|caption|col|colgroup|tbody|tr|td|th|div|dl|dd|dt|ul|ol|li|pre|form|map|area|blockquote|address|math|style|p|h[1-6]|hr|fieldset|legend|section|article|aside|hgroup|header|footer|nav|figure|figcaption|details|menu|summary)"


def wpautop(text: str) -> str:
    """Port simplifié de wpautop() (WordPress) : paragraphes et <br>."""
    if not text or not text.strip():
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n") + "\n"
    t = re.sub(r"<br\s*/?>\s*<br\s*/?>", "\n\n", t)
    t = re.sub(rf"(<{BLOCK_TAGS}[\s/>])", r"\n\n\1", t)
    t = re.sub(rf"(</{BLOCK_TAGS}>)", r"\1\n\n", t)
    t = re.sub(r"\n\n+", "\n\n", t)
    parts = [p for p in re.split(r"\n\s*\n", t) if p.strip()]
    t = "".join(f"<p>{p.strip()}</p>\n" for p in parts)
    t = re.sub(r"<p>\s*</p>", "", t)
    t = re.sub(rf"<p>\s*(</?{BLOCK_TAGS}[^>]*>)\s*</p>", r"\1", t)
    t = re.sub(rf"<p>\s*(</?{BLOCK_TAGS}[^>]*>)", r"\1", t)
    t = re.sub(rf"(</?{BLOCK_TAGS}[^>]*>)\s*</p>", r"\1", t)
    t = re.sub(r"(?<!<br />)\s*\n(?!\s*<)", "<br />\n", t)
    t = re.sub(rf"(</?{BLOCK_TAGS}[^>]*>)\s*<br />", r"\1", t)
    t = re.sub(r"<br />(\s*</?(?:p|li|div|dl|dd|dt|th|pre|td|ul|ol)[^>]*>)", r"\1", t)
    return t.strip()


ALLOWED_ATTRS = {"a": {"href", "target", "rel"}, "img": {"src", "alt"}}
DROP_TAGS_WITH_CONTENT = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.S | re.I)


def clean_html(h: str) -> str:
    """Nettoie le HTML WordPress : retire styles en ligne, spans/fonts décoratifs, attributs parasites."""
    if not h:
        return ""
    h = DROP_TAGS_WITH_CONTENT.sub("", h)
    h = re.sub(r'<div id="tango-element-highlighter".*?</div>', "", h, flags=re.S)
    h = re.sub(r"</?(?:span|font)\b[^>]*>", "", h, flags=re.I)

    def fix_tag(m):
        closing, name, attrs = m.group(1), m.group(2).lower(), m.group(3) or ""
        if closing:
            return f"</{name}>"
        keep = []
        for am in re.finditer(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("[^"]*"|\'[^\']*\')', attrs):
            if am.group(1).lower() in ALLOWED_ATTRS.get(name, set()):
                keep.append(f'{am.group(1).lower()}={am.group(2)}')
        self_close = "/" if attrs.strip().endswith("/") or name in ("br", "hr", "img") else ""
        return f"<{name}{(' ' + ' '.join(keep)) if keep else ''}{' /' if self_close else ''}>"

    h = re.sub(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b([^>]*)>", fix_tag, h)
    h = re.sub(r"<(strong|em|b|i)>(\s*)</\1>", lambda m: " " if m.group(2) else "", h)
    h = re.sub(r"<p>(?:\s|&nbsp;| )*</p>", "", h)
    h = re.sub(r"[ \t]+\n", "\n", h)
    return h.strip()


NBSP = " "


def _texturize_text(t: str) -> str:
    """Règles principales de wptexturize() avec la traduction fr_FR (guillemets « »)."""
    t = t.replace("...", "…")
    t = re.sub(r"(?<=\s)---(?=\s)", "—", t)
    t = re.sub(r"(?<=\s)--(?=\s)", "–", t)
    t = re.sub(r"(?<=\s)-(?=\s)", "–", t)
    t = re.sub(r"(?<=\d)x(?=\d)", "×", t)
    # apostrophes et guillemets simples
    t = re.sub(r"(?<=[\wÀ-ɏ\)\]\.!?,;:%])'", "’", t)
    t = re.sub(r"'(?=\d\d(?:s|\b))", "’", t)
    t = re.sub(r"(^|[\s(\[{\"«\-—–/])'", r"\1‘", t)
    t = t.replace("'", "’")
    # guillemets doubles -> « » (fr_FR)
    t = re.sub(r'(^|[\s(\[{\-—–/>])"', lambda m: m.group(1) + "«" + NBSP, t)
    t = t.replace('"', NBSP + "»")
    return t


def wptexturize(h: str) -> str:
    if not h:
        return h
    parts = re.split(r"(<[^>]*>)", h)
    out, skip = [], 0
    for p in parts:
        if p.startswith("<"):
            if re.match(r"<(code|pre|kbd|style|script)\b", p, re.I):
                skip += 1
            elif re.match(r"</(code|pre|kbd|style|script)>", p, re.I):
                skip = max(0, skip - 1)
            out.append(p)
        else:
            out.append(p if skip else _texturize_text(p))
    return "".join(out)


def rich(v: str | None) -> str:
    """Champ WYSIWYG ACF : wptexturize + wpautop + nettoyage (comme le filtre the_content)."""
    return clean_html(wpautop(wptexturize(v or "")))


def plain(v: str | None) -> str:
    return (v or "").strip()


def text_only(h: str) -> str:
    """Texte brut normalisé (pour comparer avec le rendu du site en ligne)."""
    t = re.sub(r"<br\s*/?>", " ", h or "")
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip()


def html_spans_to_parts(v: str) -> list[dict]:
    """Titres ACF du type 'nos dernières <span>réalisations</span>' -> [{text, accent}]."""
    parts = []
    for m in re.finditer(r"<span>(.*?)</span>|([^<]+)", v or ""):
        if m.group(1) is not None:
            parts.append({"text": html.unescape(m.group(1)), "accent": True})
        elif m.group(2) and m.group(2).strip():
            parts.append({"text": html.unescape(m.group(2)), "accent": False})
    return parts


# --------------------------------------------------------------------------- lecture WXR
def load():
    root = ET.parse(WXR).getroot()
    ch = root.find("channel")
    items = ch.findall("item")
    posts = {}
    for it in items:
        pid = it.findtext("wp:post_id", namespaces=NS)
        meta = {}
        for m in it.findall("wp:postmeta", namespaces=NS):
            meta[m.findtext("wp:meta_key", namespaces=NS)] = m.findtext("wp:meta_value", namespaces=NS)
        cats = [{"domain": c.get("domain"), "slug": c.get("nicename"), "name": html.unescape(c.text or "")} for c in it.findall("category")]
        posts[pid] = {
            "id": pid,
            "type": it.findtext("wp:post_type", namespaces=NS),
            "status": it.findtext("wp:status", namespaces=NS),
            "slug": it.findtext("wp:post_name", namespaces=NS) or "",
            "title": html.unescape(it.findtext("title") or ""),
            "link": it.findtext("link"),
            "date": it.findtext("wp:post_date", namespaces=NS),
            "modified": it.findtext("wp:post_modified", namespaces=NS),
            "parent": it.findtext("wp:post_parent", namespaces=NS),
            "menu_order": int(it.findtext("wp:menu_order", namespaces=NS) or 0),
            "content": it.findtext("content:encoded", namespaces=NS) or "",
            "excerpt": it.findtext("excerpt:encoded", namespaces=NS) or "",
            "attachment_url": it.findtext("wp:attachment_url", namespaces=NS),
            "cats": cats,
            "meta": meta,
        }
    terms = []
    for c in ch.findall("wp:category", namespaces=NS):
        tm = {m.findtext("wp:meta_key", namespaces=NS): m.findtext("wp:meta_value", namespaces=NS) for m in c.findall("wp:termmeta", namespaces=NS)}
        terms.append({
            "id": c.findtext("wp:term_id", namespaces=NS),
            "slug": c.findtext("wp:category_nicename", namespaces=NS),
            "name": html.unescape(c.findtext("wp:cat_name", namespaces=NS) or ""),
            "color": tm.get("colorTag"),
        })
    tags = [{"slug": t.findtext("wp:tag_slug", namespaces=NS), "name": html.unescape(t.findtext("wp:tag_name", namespaces=NS) or "")} for t in ch.findall("wp:tag", namespaces=NS)]
    return posts, terms, tags


# --------------------------------------------------------------------------- médias
# Fichiers affichés par le site en ligne différents du fichier principal de l'attachement (retouches WordPress).
FILE_OVERRIDES = {
    "1655": ("2023/04/RT_LOGO-EVENT-QTC_OK_couleurs-e1686580318732.png", None, None),
}

class Media:
    def __init__(self, posts):
        self.posts = posts
        self.used: dict[str, dict] = {}

    def ref(self, att_id, context: str) -> dict | None:
        if att_id in (None, "", "0", 0, False):
            return None
        att_id = str(att_id)
        a = self.posts.get(att_id)
        if not a or a["type"] != "attachment":
            return {"missing_attachment": att_id}
        rel = a["meta"].get("_wp_attached_file") or ""
        md = php_unserialize(a["meta"].get("_wp_attachment_metadata"))
        width = height = filesize = None
        if isinstance(md, dict):
            width, height, filesize = md.get("width"), md.get("height"), md.get("filesize")
            # Image retouchée dans WordPress : le fichier principal peut être plus petit que ses déclinaisons.
            sizes = md.get("sizes") if isinstance(md.get("sizes"), dict) else {}
            biggest = max(sizes.values(), key=lambda s: s.get("width") or 0, default=None)
            if biggest and width and width < 300 and (biggest.get("width") or 0) > width:
                rel = rel.rsplit("/", 1)[0] + "/" + biggest["file"]
                width, height, filesize = biggest.get("width"), biggest.get("height"), biggest.get("filesize")
        if att_id in FILE_OVERRIDES:
            rel, width, height = FILE_OVERRIDES[att_id]
        alt = (a["meta"].get("_wp_attachment_image_alt") or "").strip()
        entry = self.used.setdefault(att_id, {
            "id": att_id,
            "file": rel,
            "url": f"https://alunites.com/app/uploads/{rel}",
            "new_path": f"/media/{rel}",
            "width": width,
            "height": height,
            "filesize": filesize,
            "mime": (re.search(r"\.([a-z0-9]+)$", rel.lower()) or [None, None])[1],
            "alt": alt,
            "title": a["title"],
            "used_in": [],
        })
        if context not in entry["used_in"]:
            entry["used_in"].append(context)
        out = {"src": entry["new_path"]}
        if alt:
            out["alt"] = alt
        if width and height:
            out["width"], out["height"] = width, height
        return out


def ids(v) -> list[str]:
    v = php_unserialize(v) if isinstance(v, str) and is_serialized(v) else v
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, dict):
        return [str(x) for x in v.values()]
    if v in (None, ""):
        return []
    return [str(v)]


def repeater(meta: dict, prefix: str, sub: list[str]) -> list[dict]:
    n = meta.get(prefix)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return []
    rows = []
    for i in range(n):
        rows.append({k: meta.get(f"{prefix}_{i}_{k}") for k in sub})
    return rows


def vimeo_id(url: str | None) -> str | None:
    m = re.search(r"(?:vimeo\.com/(?:video/)?|playback/)(\d{6,})", url or "")
    return m.group(1) if m else None


# --------------------------------------------------------------------------- contenus
def seo(meta: dict, media: Media, ctx: str) -> dict:
    out = {"meta_title": plain(meta.get("meta_title")), "meta_description": plain(meta.get("meta_description"))}
    img = media.ref(meta.get("meta_image"), ctx + ":seo")
    if img:
        out["meta_image"] = img
    return out


def blocks(meta: dict, media: Media, ctx: str) -> list[dict]:
    layout = ids(meta.get("blocks"))
    out = []
    for i, name in enumerate(layout):
        p = f"blocks_{i}_"
        if name == "text_block":
            texts = [rich(r["text"]) for r in repeater(meta, f"blocks_{i}_texts", ["text"])]
            body = "\n".join(t for t in texts if t)
            if body:  # le thème n'affiche pas les blocs texte vides
                out.append({"type": "text", "body": body})
        elif name == "quote_block":
            out.append({"type": "quote", "quote": rich(meta.get(p + "quote")), "author": clean_html(plain(meta.get(p + "author")))})
        elif name == "image_block":
            img = media.ref(meta.get(p + "image"), ctx)
            out.append({"type": "image", "style": meta.get(p + "style") or "fullscreen", "image": img})
        elif name == "slider_block":
            imgs = [media.ref(x, ctx) for x in ids(meta.get(p + "gallery"))]
            out.append({"type": "slider", "images": [x for x in imgs if x]})
        elif name == "video_block":
            url = plain(meta.get(p + "video_url"))
            out.append({"type": "video", "style": meta.get(p + "style") or "fullscreen", "vimeo": vimeo_id(url), "video_url": url, "cover": media.ref(meta.get(p + "cover"), ctx)})
        else:
            out.append({"type": "unknown", "layout": name})
    return out


def keywords(meta):
    return [plain(r["key"]) for r in repeater(meta, "header_keyword", ["key"]) if plain(r["key"])]


def hook_lines(v: str | None) -> list[str]:
    h = clean_html(wpautop(wptexturize(v or "")))
    lines = re.findall(r"<p>(.*?)</p>", h, flags=re.S)
    if not lines and h:
        lines = [h]
    return [html.unescape(re.sub(r"<[^>]+>", "", l)).replace(" ", " ").strip() for l in lines if re.sub(r"<[^>]+>", "", l).strip()]


def main() -> int:
    posts, terms, tags = load()
    media = Media(posts)
    by_type: dict[str, list[dict]] = {}
    for p in posts.values():
        by_type.setdefault(p["type"], []).append(p)

    def slug_of(pid):
        p = posts.get(str(pid))
        return p["slug"] if p else None

    expertise_slug = {p["id"]: p["slug"] for p in by_type.get("expertise", [])}

    projects = []
    for p in by_type.get("project", []):
        m = p["meta"]
        ctx = f"project:{p['slug'] or p['id']}"
        projects.append({
            "wp_id": p["id"], "status": p["status"], "slug": p["slug"], "title": p["title"], "date": p["date"], "modified": p["modified"],
            "menu_order": p["menu_order"],
            "expertises": [expertise_slug.get(x, x) for x in ids(m.get("expertises"))],
            "client": plain(m.get("header_client")),
            "cover": media.ref(m.get("header_cover"), ctx + ":cover"),
            "hook": hook_lines(m.get("header_hook")),
            "chapeau": rich(m.get("header_chapeau")),
            "intro": clean_html(wpautop(m.get("header_text") or "")),  # textarea : pas de wptexturize
            "keywords": keywords(m),
            "cta": {"label": plain(m.get("header_cta_cta_label")), "link": php_unserialize(m.get("header_cta_cta_link")) if is_serialized(m.get("header_cta_cta_link")) else plain(m.get("header_cta_cta_link"))},
            "home_slider": {"image": media.ref(m.get("header_image_slider_home"), ctx + ":home"), "video_url": plain(m.get("header_video_slider_home")), "vimeo": vimeo_id(m.get("header_video_slider_home"))},
            "blocks": blocks(m, media, ctx),
            "suggestions": [slug_of(x) for x in ids(m.get("suggestions"))],
            "seo": seo(m, media, ctx),
        })

    articles = []
    cat_terms = {t["slug"]: t for t in terms}
    for p in by_type.get("post", []):
        m = p["meta"]
        ctx = f"post:{p['slug'] or p['id']}"
        articles.append({
            "wp_id": p["id"], "status": p["status"], "slug": p["slug"], "title": p["title"], "date": p["date"], "modified": p["modified"],
            "categories": [c["slug"] for c in p["cats"] if c["domain"] == "category"],
            "tags": [c["slug"] for c in p["cats"] if c["domain"] == "post_tag"],
            "expertises": [expertise_slug.get(x, x) for x in ids(m.get("expertises"))],
            "client": plain(m.get("header_client")),
            "header_date": plain(m.get("header_date")),
            "cover": media.ref(m.get("header_cover"), ctx + ":cover"),
            "hook": hook_lines(m.get("header_hook")),
            "chapeau": rich(m.get("header_chapeau")),
            "intro": clean_html(wpautop(m.get("header_text") or "")),  # textarea : pas de wptexturize
            "keywords": keywords(m),
            "link": plain(m.get("header_link")),
            "home_slider": {"video_url": plain(m.get("header_video_slider_home")), "vimeo": vimeo_id(m.get("header_video_slider_home"))},
            "blocks": blocks(m, media, ctx),
            "suggestions": [slug_of(x) for x in ids(m.get("suggestions"))],
            "seo": seo(m, media, ctx),
            "content": p["content"],
        })

    expertises = []
    for p in by_type.get("expertise", []):
        m = p["meta"]
        ctx = f"expertise:{p['slug']}"
        expertises.append({
            "wp_id": p["id"], "slug": p["slug"], "title": p["title"], "menu_order": p["menu_order"],
            "resume": plain(m.get("resume")),
            "color": m.get("colorTag"),
            "introduction": rich(m.get("header_introduction")),
            "objectifs_title": plain(m.get("header_objectif_title")),
            "objectifs": [plain(r["objectif"]) for r in repeater(m, "header_objectifs", ["objectif"])],
            "video": {"vimeo": vimeo_id(m.get("video_video_url")), "video_url": plain(m.get("video_video_url")), "cover": media.ref(m.get("video_cover"), ctx)},
            "activity_title": html_spans_to_parts(m.get("activity_title")),
            "activities": [{"title": plain(r["title"]), "body": rich(r["text"])} for r in repeater(m, "activity_list", ["title", "text"])],
            "icons": [{"title": plain(r["title"]), "icon": media.ref(r["icon"], ctx + ":icon")} for r in repeater(m, "icons_iconsList", ["title", "icon"])],
            "contact_quote": plain(m.get("contact_quote")),
            "contact_people": [slug_of(x) for x in ids(m.get("contact_people"))],
            "suggestions": [slug_of(x) for x in ids(m.get("suggestions"))],
            "seo": seo(m, media, ctx),
        })

    people = []
    for p in by_type.get("people", []):
        m = p["meta"]
        ctx = f"people:{p['slug']}"
        job_raw = m.get("content_job") or ""
        people.append({
            "wp_id": p["id"], "status": p["status"], "slug": p["slug"], "name": p["title"], "date": p["date"], "menu_order": p["menu_order"],
            "job": re.sub(r"\s+", " ", html.unescape(re.sub(r"<br\s*/?>", " — ", re.sub(r"</?font[^>]*>", "", job_raw)))).strip(" —"),
            "job_html": clean_html(job_raw),
            "quote": plain(m.get("content_description")),
            "email": plain(m.get("content_mail")),
            "photo": media.ref(m.get("content_cover"), ctx),
            "photo_hover": media.ref(m.get("content_hover_cover"), ctx),
        })

    jobs = []
    for p in by_type.get("job", []):
        m = p["meta"]
        jobs.append({"wp_id": p["id"], "status": p["status"], "slug": p["slug"], "title": p["title"], "date": p["date"], "old_url": p["link"], "pdf": media.ref(m.get("content_pdf"), f"job:{p['slug']}")})

    pages = {}
    for key, pid in LIVE_PAGE_IDS.items():
        p = posts[pid]
        m = p["meta"]
        ctx = f"page:{key}"
        base = {"wp_id": pid, "slug": p["slug"], "title": p["title"], "date": p["date"], "modified": p["modified"], "seo": seo(m, media, ctx)}
        if key == "home":
            base.update({
                "slider_items": [slug_of(x) for x in ids(m.get("header_projets"))],
                "slider_item_types": [posts[x]["type"] for x in ids(m.get("header_projets")) if x in posts],
                "agency_text": rich(m.get("agency_text")),
                "expertise_title": html_spans_to_parts(m.get("expertise_title")),
                "expertise_text_1": rich(m.get("expertise_text_1")),
                "expertise_text_2": rich(m.get("expertise_text_2")),
                "news_title": plain(m.get("news_title")),
                "news": [slug_of(x) for x in ids(m.get("news_suggests"))],
            })
        elif key == "agence":
            base.update({
                "header_title": html_spans_to_parts(m.get("header_title")),
                "header_presentation": rich(m.get("header_presentation")),
                "numbers_title": html_spans_to_parts(m.get("numbers_title")),
                "numbers_subtitle": plain(m.get("numbers_subtitle")),
                "global_numbers": [{"number": r["number"], "label": plain(r["number_label"]), "title": plain(r["title"])} for r in repeater(m, "numbers_global_numbers", ["number", "number_label", "title"])],
                "years_title": plain(m.get("numbers_years_title")),
                "year_numbers": [{"number": r["number"], "title": plain(r["title"]), "picto": media.ref(r["picto"], ctx + ":picto")} for r in repeater(m, "numbers_year_numbers", ["number", "number_label", "title", "picto"])],
                "presentation_title": plain(m.get("presentation_title")),
                "presentation_subtitle": plain(m.get("presentation_subtitle")),
                "presentation_text_head": rich(m.get("presentation_text_head")),
                "presentation_text": rich(m.get("presentation_text")),
                "presentation_image": media.ref(m.get("presentation_image"), ctx),
                "values_title": html_spans_to_parts(m.get("values_title")),
                "values_subtitle": plain(m.get("values_subtitle")),
                "values": [{"title": plain(r["title"]), "body": rich(r["text"])} for r in repeater(m, "values_values", ["title", "text"])],
                "trust_title": html_spans_to_parts(m.get("trust_title")),
                "trust_subtitle": plain(m.get("trust_subtitle")),
                "clients": [x for x in (media.ref(i, ctx + ":clients") for i in ids(m.get("trust_gallery"))) if x],
                "people_title": html_spans_to_parts(m.get("people_title")),
                "join_title": html_spans_to_parts(m.get("join_title")),
                "join_subtitle": plain(m.get("join_subtitle")),
            })
        elif key == "contact":
            base.update({
                "cover": media.ref(m.get("content_cover"), ctx),
                "title": html_spans_to_parts(m.get("content_title")),
                "subtitle": plain(m.get("content_subtitle")),
                "description": plain(m.get("content_description")),
                "placeholders": {"name": plain(m.get("content_name_placeholder")), "email": plain(m.get("content_email_placeholder")), "message": plain(m.get("content_message_placeholder"))},
                "fun_title": html_spans_to_parts(m.get("fun_block_title")),
                "fun_description": plain(m.get("fun_block_description")),
                "fun_button": plain(m.get("fun_block_spinButton")),
                "mantras": [[plain(m.get(f"fun_block_textBlocks_{i}_content_{j}_text")) for j in range(int(m.get(f"fun_block_textBlocks_{i}_content") or 0))] for i in range(int(m.get("fun_block_textBlocks") or 0))],
            })
        elif key == "mentions-legales":
            base.update({"heading": plain(m.get("content_title")), "body": rich(m.get("content_text"))})
        else:
            base.update({"heading": html_spans_to_parts(m.get("content_title"))})
        pages[key] = base

    nav = [{"id": p["id"], "order": p["menu_order"], "object_id": p["meta"].get("_menu_item_object_id"), "object": p["meta"].get("_menu_item_object"), "url": p["meta"].get("_menu_item_url"), "title": p["title"]} for p in sorted(by_type.get("nav_menu_item", []), key=lambda x: x["menu_order"])]
    for n in nav:
        n["target_slug"] = slug_of(n["object_id"])

    # PDF & fichiers rattachés directement (offres) déjà comptés ; ajoute pictos d'expertise etc. via ref()
    OUT.mkdir(parents=True, exist_ok=True)
    content = {
        "categories": [t for t in terms if t["slug"] not in ("uncategorized", "non-classe")],
        "tags": tags,
        "projects": projects,
        "articles": articles,
        "expertises": expertises,
        "people": people,
        "jobs": jobs,
        "pages": pages,
        "nav": nav,
    }
    (OUT / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=1))
    med = sorted(media.used.values(), key=lambda x: x["file"])
    (OUT / "media.json").write_text(json.dumps(med, ensure_ascii=False, indent=1))
    total = sum(x["filesize"] or 0 for x in med)
    missing = [x for x in med if x.get("missing_attachment")]
    print(f"projets={len(projects)} articles={len(articles)} expertises={len(expertises)} équipe={len(people)} offres={len(jobs)}")
    print(f"médias référencés={len(med)} taille≈{total/1e6:.1f} Mo (filesize WP connu pour {sum(1 for x in med if x['filesize'])})")
    unknown = [(p['slug'], b['layout']) for p in projects + articles for b in p['blocks'] if b['type'] == 'unknown']
    if unknown:
        print("Blocs inconnus:", unknown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
