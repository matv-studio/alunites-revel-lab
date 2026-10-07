#!/usr/bin/env python3
"""Vérifie l'intégrité des fichiers bruts extraits du site actuel.

Chaque élément est re-sérialisé comme JSON.stringify (séparateurs compacts,
pas d'échappement ASCII) puis comparé à la longueur et au hash FNV-1a 32 bits
calculés dans le navigateur au moment de l'extraction.
"""
import json
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"


def fnv1a(s: str) -> str:
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return format(h, "x")


def dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def main() -> int:
    hashes = json.loads((RAW / "hashes.json").read_text())
    ok = bad = missing = 0
    for kind in ("projects", "posts"):
        items = {}
        for f in sorted(RAW.glob(f"{kind}-*.json")):
            for it in json.loads(f.read_text()):
                items[it["slug"]] = it
        for slug, ln, h in hashes[kind]:
            it = items.get(slug)
            if it is None:
                missing += 1
                print(f"MANQUANT {kind}/{slug}")
                continue
            s = dumps(it)
            if len(s.encode("utf-16-le")) // 2 == ln and fnv1a(s) == h:
                ok += 1
            else:
                bad += 1
                print(f"ÉCART   {kind}/{slug}: len {len(s)} vs {ln}, hash {fnv1a(s)} vs {h}")
    pages_file = RAW / "pages.json"
    if pages_file.exists():
        pages = json.loads(pages_file.read_text())
        for k, (ln, h) in hashes["pages"].items():
            if k not in pages:
                missing += 1
                print(f"MANQUANT pages/{k}")
                continue
            s = dumps(pages[k])
            if len(s.encode("utf-16-le")) // 2 == ln and fnv1a(s) == h:
                ok += 1
            else:
                bad += 1
                print(f"ÉCART   pages/{k}: len {len(s)} vs {ln}, hash {fnv1a(s)} vs {h}")
    else:
        missing += len(hashes["pages"])
        print("MANQUANT pages.json")
    svg_file = RAW / "svgs.json"
    if svg_file.exists():
        svgs = json.loads(svg_file.read_text())
        for k, (ln, h) in hashes["svgs"].items():
            s = dumps(svgs.get(k))
            if len(s.encode("utf-16-le")) // 2 == ln and fnv1a(s) == h:
                ok += 1
            else:
                bad += 1
                print(f"ÉCART   svgs/{k}: len {len(s)} vs {ln}")
    else:
        missing += len(hashes["svgs"])
        print("MANQUANT svgs.json")
    print(f"OK={ok} ÉCARTS={bad} MANQUANTS={missing}")
    return 0 if bad == 0 and missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
