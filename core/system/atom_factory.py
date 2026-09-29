#!/usr/bin/env python3
"""atom_factory.py (generički) — jedini izvor istine za atome ovog domena.

SR: Laki factory za domene čiji su atomi uglavnom ručno pisani (persone/komande/
    alati/naučeno). Daje: helper-e, `write_atom`/`finalize` (vreme kreiranja na
    svakom atomu), generator tool/skill atoma iz cell.json, i backfill vremena u
    postojeće atome. Budući kod (import/upload) treba da zove OVO, ne da kopira.
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(text: object) -> str:
    norm = unicodedata.normalize("NFKD", str(text))
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")[:80] or "atom"


def y(v: object) -> str:
    s = "" if v is None else str(v)
    if s == "":
        return '""'
    if re.search(r'[:#\[\]{}",\'\n]|^\s|\s$', s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


_CREATED_RE = re.compile(r'^atom_kreiran:\s*(.+)$', re.MULTILINE)


def _existing_created(path: Path) -> str | None:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = _CREATED_RE.search(txt)
    return m.group(1).strip() if m else None


def finalize(content: str, path: Path, ts: str | None = None) -> str:
    """Ubaci atom_kreiran (očuvano) + atom_azuriran u frontmatter."""
    if _CREATED_RE.search(content):
        return content
    ts = ts or now_iso()
    created = _existing_created(path) or ts
    inject = f"atom_kreiran: {created}\natom_azuriran: {ts}\n"
    if content.startswith("---\n"):
        return "---\n" + inject + content[4:]
    return "---\n" + inject + "---\n\n" + content



def _v3_source_path(head, path):
    import re as _re
    from pathlib import Path as _P
    if _re.search(r"^source_path:", head, _re.MULTILINE):
        return None
    sp = str(path)
    for mark in (".ai/atomi", "Actors", ".ai/"):
        i = sp.find(mark)
        if i >= 0:
            sp = sp[i:]
            break
    else:
        sp = _P(path).name
    return "source_path: " + sp


def _v3_summary(head, body):
    import json as _json
    import re as _re
    if _re.search(r"^summary:", head, _re.MULTILINE):
        return None
    first = ""
    for ln in body.splitlines():
        s = ln.strip()
        if s and s[0] not in "#[|`":
            s = _re.sub(r"^[-*>]\s*", "", s)
            s = _re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
            if len(s) >= 12:
                first = s[:140]
                break
    tm = _re.search(r"^title:\s*(.+)$", head, _re.MULTILINE)
    summ = first or (tm.group(1).strip().strip("'\"") if tm else "")
    return ("summary: " + _json.dumps(summ, ensure_ascii=False)) if summ else None


def _v3_keywords(head):
    import re as _re
    if _re.search(r"^keywords:", head, _re.MULTILINE):
        return None
    words = []
    tm = _re.search(r"^title:\s*(.+)$", head, _re.MULTILINE)
    if tm:
        words += [w for w in _re.sub(r"[^a-z0-9 ]", " ", tm.group(1).lower()).split() if len(w) > 2]
    ga = _re.search(r"^glavni_akteri:\s*\[(.*?)\]", head, _re.MULTILINE)
    if ga:
        words += [x.strip().lower() for x in ga.group(1).split(",") if x.strip()]
    for fld in ("kategorija", "media_type", "status_videa", "profesije"):
        fm2 = _re.search(r"^" + fld + r":\s*(.+)$", head, _re.MULTILINE)
        if fm2:
            words.append(fm2.group(1).strip().strip("[]'\"").lower())
    seen = []
    for w in words:
        w = w.strip()
        if w and w not in seen:
            seen.append(w)
    return ("keywords: [" + ", ".join(seen[:12]) + "]") if seen else None


def _v3_edges(head, body):
    import re as _re
    if _re.search(r"^edges:", head, _re.MULTILINE):
        return None
    tgts = []
    for lt in _re.findall(r"\[\[([^\]]+)\]\]", body):
        t = _re.sub(r"[^a-z0-9]+", "-", lt.lower()).strip("-")
        if t and t not in tgts:
            tgts.append(t)
    if not tgts:
        return None
    return "edges:\n" + "\n".join(
        "- {type: references, target: " + t + ", weight: 0.5}" for t in tgts[:20]
    )


def _ensure_v3(content: str, path) -> str:
    """Best-effort v3 dopuna (summary/keywords/source_path/edges). Nikad ne baca."""
    try:
        if not content.startswith("---\n"):
            return content
        head = content.split("\n---", 1)[0]
        body = content.split("\n---", 1)[1] if "\n---" in content else ""
        ins = [x for x in (_v3_source_path(head, path), _v3_summary(head, body),
                           _v3_keywords(head), _v3_edges(head, body)) if x]
        if not ins:
            return content
        return content.replace("---\n", "---\n" + "\n".join(ins) + "\n", 1)
    except Exception:  # noqa: BLE001
        return content


def write_atom(path: Path, content: str, ts: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_ensure_v3(finalize(content, path, ts), path), encoding="utf-8")


def build_tool_skill_atoms(tools: list[dict], skills: list[dict]) -> tuple[dict, dict, list, list]:
    """slug->content za alate/veštine iz cell.json (AI-namenjeni, generički)."""
    def one(kind: str, item: dict) -> tuple[str, str]:
        name = item.get("name", "?")
        slug = slugify(name)
        item["slug"] = slug
        kat = "Alat" if kind == "tool" else "Veština"
        L = ["---", f"id: {slug}", f"type: {kind}", "domain: os",
             f"title: {y(name)}", f"kategorija: {kat}", f'ikona: {y(item.get("icon", "wrench"))}',
             f'namena: {y(item.get("description", ""))}', f"tags: [{'alat' if kind=='tool' else 'vestina'}]",
             "---", "", "## 🎯 ŠTA JE", item.get("description", name), "",
             "## 🤖 KADA AI OVO KORISTI", "Po potrebi domena (dopuniti kurirano)."]
        return slug, "\n".join(L).rstrip() + "\n"
    ta = dict(one("tool", t) for t in tools)
    sa = dict(one("skill", s) for s in skills)
    return ta, sa, tools, skills


def backfill_timestamps(atomi_root: Path) -> tuple[int, int]:
    """Ubaci vreme kreiranja (= mtime) u sve .md atome bez njega."""
    done = skip = 0
    for dp, dns, fns in os.walk(atomi_root):
        dns[:] = [x for x in dns if x not in ("__pycache__", ".git")]
        for fn in fns:
            if not fn.endswith(".md"):
                continue
            p = Path(dp, fn)
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _CREATED_RE.search(txt):
                skip += 1
                continue
            ts = datetime.fromtimestamp(p.stat().st_mtime).astimezone().replace(microsecond=0).isoformat()
            inject = f"atom_kreiran: {ts}\natom_azuriran: {ts}\n"
            new = ("---\n" + inject + txt[4:]) if txt.startswith("---\n") else ("---\n" + inject + "---\n\n" + txt)
            try:
                p.write_text(new, encoding="utf-8")
                done += 1
            except OSError:
                pass
    return done, skip
