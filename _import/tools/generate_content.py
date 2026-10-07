#!/usr/bin/env python3
"""Génère les fichiers de contenu Eleventy / Pages CMS à partir de _import/data/content.json.

- src/content/projets/*.md, actualites/*.md, expertises/*.md, equipe/*.md, offres/*.md
- src/_data/pages/*.yml, src/_data/site.yml, src/_data/clients.yml, src/_data/categories.yml

Conventions :
- Les titres de section utilisent *mot* pour un mot mis en couleur (rendu <em class="accent">).
- Les champs riches sont en HTML (Pages CMS : rich-text format html).
- Les médias pointent vers /media/AAAA/MM/fichier (ancien /app/uploads/AAAA/MM/fichier, redirigé en 301).
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "_import" / "data" / "content.json"
SRC = ROOT / "src"


# --------------------------------------------------------------------------- YAML
class Dumper(yaml.SafeDumper):
    pass


def _str(dumper, s):
    if "\n" in s:
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", s)


Dumper.add_representer(str, _str)


def dump(obj) -> str:
    return yaml.dump(obj, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=100000, default_flow_style=False)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def frontmatter(data: dict, body: str = "") -> str:
    return "---\n" + dump(clean(data)) + "---\n" + (body.strip() + "\n" if body.strip() else "")


def clean(o):
    """Retire les clés vides (None, '', [], {}) pour des fichiers lisibles."""
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            v = clean(v)
            if v in (None, "", [], {}):
                continue
            out[k] = v
        return out
    if isinstance(o, list):
        return [clean(x) for x in o if clean(x) not in (None, "", [], {})]
    return o


# --------------------------------------------------------------------------- helpers
def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parts_to_marked(parts) -> str:
    """[{text, accent}] -> 'nos dernières *réalisations*' (les <span> du thème deviennent *…*)."""
    out = ""
    for p in parts or []:
        t = p["text"]
        core = t.strip()
        if not core:
            out += " "
            continue
        piece = f"*{core}*" if p["accent"] else core
        if out and not out.endswith(" ") and (p["accent"] or t[:1].isspace() or out.endswith("*")):
            out += " "
        out += piece
        if t[-1:].isspace():
            out += " "
    return re.sub(r"\s+", " ", out).strip()


def img(ref):
    return ref.get("src") if isinstance(ref, dict) else None


def alt(ref):
    return ref.get("alt") if isinstance(ref, dict) else None


def wp_date(d: str | None) -> str | None:
    return d.replace(" ", "T") if d else None


def header_date(v: str | None, fallback: str | None) -> str | None:
    if v and re.fullmatch(r"\d{8}", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}"
    if v and re.match(r"\d{4}-\d{2}-\d{2}", v):
        return v[:10]
    return fallback[:10] if fallback else None


def seo(s: dict) -> dict:
    return {"title": s.get("meta_title"), "description": s.get("meta_description"), "image": img(s.get("meta_image"))}


def blocks(bs: list[dict]) -> list[dict]:
    out = []
    for b in bs:
        t = b["type"]
        if t == "text":
            out.append({"type": "text", "body": b["body"]})
        elif t == "quote":
            out.append({"type": "quote", "quote": b["quote"], "author": b.get("author")})
        elif t == "image":
            if not b.get("image"):
                continue
            out.append({"type": "image", "style": b.get("style"), "image": img(b["image"]), "alt": alt(b["image"])})
        elif t == "slider":
            out.append({"type": "slider", "images": [img(x) for x in b["images"]]})
        elif t == "video":
            out.append({"type": "video", "style": b.get("style"), "video": b.get("video_url"), "cover": img(b.get("cover"))})
    return out


# --------------------------------------------------------------------------- génération
def main() -> int:
    c = json.loads(DATA.read_text())
    used_slugs: set[str] = set()

    def ensure_slug(p, prefix):
        s = p["slug"] or slugify(p.get("title") or p.get("name") or p["wp_id"])
        s = re.sub(r"%[0-9a-f]{2}", "", s, flags=re.I)  # %c2%b7 (point médian) dans les slugs d'offres
        s = re.sub(r"-+", "-", s).strip("-")
        if (prefix, s) in used_slugs:
            s = f"{s}-{p['wp_id']}"
        used_slugs.add((prefix, s))
        return s

    # ---------------- projets
    for p in c["projects"]:
        slug = ensure_slug(p, "projets")
        fm = {
            "title": p["title"],
            "slug": slug,
            "published": p["status"] == "publish",
            "date": wp_date(p["date"]),
            "client": p["client"],
            "expertises": p["expertises"],
            "cover": img(p["cover"]),
            "cover_alt": alt(p["cover"]),
            "hook": p["hook"],
            "chapeau": p["chapeau"],
            "intro": p["intro"],
            "keywords": p["keywords"],
            "home_video": p["home_slider"].get("video_url"),
            "blocks": blocks(p["blocks"]),
            "suggestions": [s for s in p["suggestions"] if s],
            "seo": seo(p["seo"]),
            "wp_id": int(p["wp_id"]),
        }
        write(SRC / "content" / "projets" / f"{slug}.md", frontmatter(fm))

    # ---------------- actualités
    for p in c["articles"]:
        slug = ensure_slug(p, "actualites")
        fm = {
            "title": p["title"],
            "slug": slug,
            "published": p["status"] == "publish",
            "date": wp_date(p["date"]),
            "display_date": header_date(p["header_date"], p["date"]),
            "categories": p["categories"],
            "expertises": p["expertises"],
            "cover": img(p["cover"]),
            "cover_alt": alt(p["cover"]),
            "hook": p["hook"],
            "chapeau": p["chapeau"],
            "intro": p["intro"],
            "keywords": p["keywords"],
            "link": p["link"] if p["link"] and "google.com" not in p["link"] else None,
            "home_video": p["home_slider"].get("video_url"),
            "blocks": blocks(p["blocks"]),
            "suggestions": [s for s in p["suggestions"] if s],
            "seo": seo(p["seo"]),
            "wp_id": int(p["wp_id"]),
        }
        write(SRC / "content" / "actualites" / f"{slug}.md", frontmatter(fm))

    # ---------------- expertises
    for e in c["expertises"]:
        fm = {
            "title": e["title"],
            "slug": e["slug"],
            "order": e["menu_order"],
            "color": e["color"],
            "summary": e["resume"],
            "introduction": e["introduction"],
            "sectors_title": e["objectifs_title"],
            "sectors": e["objectifs"],
            "video": e["video"].get("video_url"),
            "video_cover": img(e["video"].get("cover")),
            "activities_title": parts_to_marked(e["activity_title"]),
            "activities": e["activities"],
            "formats": [{"title": i["title"], "icon": img(i["icon"])} for i in e["icons"]],
            "contact_quote": re.sub(r"\s+", " ", re.sub(r"</?span>", " ", e["contact_quote"])).strip(),
            "contact_person": (e["contact_people"] or [None])[0],
            "suggestions": [s for s in e["suggestions"] if s],
            "seo": seo(e["seo"]),
            "wp_id": int(e["wp_id"]),
        }
        write(SRC / "content" / "expertises" / f"{e['slug']}.md", frontmatter(fm))

    # ---------------- équipe
    for p in c["people"]:
        slug = ensure_slug(p, "equipe")
        fm = {
            "name": p["name"],
            "slug": slug,
            "published": p["status"] == "publish",
            "order": p["menu_order"],
            "job": p["job"],
            "quote": p["quote"],
            "email": p["email"],
            "photo": img(p["photo"]),
            "photo_hover": img(p["photo_hover"]),
            "wp_id": int(p["wp_id"]),
        }
        write(SRC / "content" / "equipe" / f"{slug}.md", frontmatter(fm))

    # ---------------- offres
    for j in c["jobs"]:
        slug = ensure_slug(j, "offres")
        fm = {
            "title": j["title"],
            "slug": slug,
            "published": j["status"] == "publish",
            "date": wp_date(j["date"]),
            "pdf": img(j["pdf"]),
            "old_url": j["old_url"],
            "wp_id": int(j["wp_id"]),
        }
        write(SRC / "content" / "offres" / f"{slug}.md", frontmatter(fm))

    # ---------------- pages (fichiers uniques)
    P = c["pages"]
    h, a, ct, lg = P["home"], P["agence"], P["contact"], P["mentions-legales"]
    pages = {
        "accueil": {
            "seo": seo(h["seo"]),
            "featured": h["slider_items"],
            "agency_text": h["agency_text"],
            "expertises_title": parts_to_marked(h["expertise_title"]),
            "expertises_text_1": h["expertise_text_1"],
            "expertises_text_2": h["expertise_text_2"],
            "news_title": h["news_title"],
            "news": ["alunites-a-tout-prix", "le-podmotion-kesako", "comment-le-brand-content-peut-il-remplir-vos-objectifs"],
        },
        "agence": {
            "seo": seo(a["seo"]),
            "title": parts_to_marked(a["header_title"]),
            "intro": a["header_presentation"],
            "numbers_title": parts_to_marked(a["numbers_title"]),
            "numbers_subtitle": a["numbers_subtitle"],
            "numbers": [{"value": int(n["number"]), "unit": n["label"], "label": n["title"]} for n in a["global_numbers"]],
            "yearly_title": a["years_title"],
            "yearly_numbers": [{"value": int(n["number"]), "label": n["title"], "picto": img(n["picto"])} for n in a["year_numbers"]],
            "story_title": a["presentation_title"],
            "story_subtitle": a["presentation_subtitle"],
            "story_lead": a["presentation_text_head"],
            "story_text": a["presentation_text"],
            "story_image": img(a["presentation_image"]),
            "values_title": parts_to_marked(a["values_title"]),
            "values_subtitle": a["values_subtitle"],
            "values": a["values"],
            "clients_title": parts_to_marked(a["trust_title"]),
            "clients_subtitle": a["trust_subtitle"],
            "team_title": parts_to_marked(a["people_title"]),
            "jobs_title": parts_to_marked(a["join_title"]),
            "jobs_subtitle": a["join_subtitle"],
        },
        "contact": {
            "seo": seo(ct["seo"]),
            "title": parts_to_marked(ct["title"]),
            "subtitle": ct["subtitle"],
            "description": ct["description"],
            "cover": img(ct["cover"]),
            "placeholders": ct["placeholders"],
            "compass_title": parts_to_marked(ct["fun_title"]),
            "compass_description": ct["fun_description"],
            "compass_button": ct["fun_button"],
            "mantras": [{"lines": m} for m in ct["mantras"]],
        },
        "mentions-legales": {"seo": seo(lg["seo"]), "title": lg["heading"], "body": lg["body"]},
        "projets": {"seo": seo(P["projets"]["seo"]), "title": parts_to_marked(P["projets"]["heading"])},
        "actualites": {"seo": seo(P["actualites"]["seo"]), "title": parts_to_marked(P["actualites"]["heading"])},
    }
    for k, v in pages.items():
        write(SRC / "_data" / "pages" / f"{k}.yml", dump(clean(v)))

    clients = [{"logo": x["src"], "name": (x.get("alt") or Path(x["src"]).stem.replace("-", " ").replace("_", " ")).strip()} for x in a["clients"]]
    write(SRC / "_data" / "clients.yml", dump({"logos": clients}))

    cats = [{"slug": t["slug"], "name": t["name"], "color": t["color"]} for t in c["categories"]]
    write(SRC / "_data" / "rubriques.yml", dump({"items": cats}))

    print("Contenus générés dans", SRC)
    return 0


if __name__ == "__main__":
    sys.exit(main())
