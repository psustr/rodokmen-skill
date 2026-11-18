#!/usr/bin/env python3
"""Lánové rejstříky (Morava 1656–1679, MZA Brno, fond D 1, ARON).
Použití (spouštěj z kořene projektu: python3 -I tools/lanove.py …):
  hledat "Obec"            knihy, kde je obec (podle obcí v popisu knihy a názvu panství) – první běh stáhne index
  index [--obnovit]        jednorázový index všech 372 knih fondu (jen popisy, žádné snímky; ~15 min, pauza 2 s)
  info <apu>               panství, roky, signatura, obce z popisu, počet snímků
  snimek <apu> <n> <out.jpg> [x0,y0,x1,y1]
                           snímek n (1…) uloží PROHLÍŽEČ (tools/aron_obrazovka.sh: prohlížeč obrázků v kartě matrik
                           MZA, jako „Uložit obrázek jako“; i se skrytým oknem); oblast = přiblížení části snímku
                           (zlomky 0–1, např. pravá strana 0.5,0,1,1) – vyšší rozlišení
  link <apu> <n>           odkaz na snímek v ARONu (do zaznamy.json „odkaz“)
  svazek <apu>             zapíše knihu do data/svazky.json (klíč „lr“ + 6 znaků apu)
Metadata (popisy knih) stahuje skript s poctivou identifikací; snímky jen prohlížeč (žádné dlaždice skriptem)."""
import gzip, json, os, re, subprocess, sys, time, unicodedata, urllib.request
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

API = "https://www.mza.cz/aron/api/aron"
SERIE = "f8ff279b-aa5f-448e-a55c-7c8fea9a432d"   # MZA, D 1 Lánové rejstříky, série Úřední knihy (372 knih)
UA = "rodokmen-skill (+https://github.com/psustr/rodokmen-skill)"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "rodokmen-lanove")
PAUZA = 2.0


def get(path, tries=3):
    req = urllib.request.Request(API + path, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b":
                    b = gzip.decompress(b)
                return json.loads(b)
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(10 * (attempt + 1))


def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def parse(apu):
    """Z detailu knihy: název, roky, signatura, obce (entity J_G), soubory snímků (id v pořadí)."""
    r = json.loads(apu.get("result") or "{}")
    vals = {}
    for row in r.get("l", []):
        for cell in row:
            vals.setdefault(cell.get("t"), []).extend(v.get("v") for v in cell.get("v", []) if v.get("v"))
    files, dzi = [], []
    for do in apu.get("digitalObjects") or []:
        for f in sorted(do.get("files") or [], key=lambda f: f.get("order") or 0):
            if f.get("type") == "TILE":
                files.append(f["id"]); dzi.append(f.get("referencedFile") or "")
    return {"id": apu["id"], "nazev": apu.get("name"), "roky": (vals.get("D") or [""])[0],
            "signatura": (vals.get("J_S") or [""])[0], "obce": vals.get("J_G") or [], "soubory": files, "dzi": dzi}


def kniha(apu_id):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, apu_id + ".json")
    if os.path.exists(f):
        k = json.load(open(f, encoding="utf-8"))
        if "dzi" in k:
            return k
    k = parse(get("/apu/" + apu_id))
    json.dump(k, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    return k


def index(obnovit=False):
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, "index.json")
    if os.path.exists(f) and not obnovit:
        return json.load(open(f, encoding="utf-8"))
    tree = get(f"/apu/{SERIE}/tree")
    knihy = [{"id": c["id"], "nazev": c["name"]} for c in tree.get("children", [])]
    print(f"index: {len(knihy)} knih – stahuji popisy (jen text, pauza {PAUZA} s) …", file=sys.stderr)
    out = []
    for i, k in enumerate(knihy, 1):
        cached = os.path.exists(os.path.join(CACHE, k["id"] + ".json"))
        d = kniha(k["id"])
        out.append({kk: d[kk] for kk in ("id", "nazev", "roky", "signatura", "obce")} | {"snimku": len(d["soubory"])})
        if not cached:
            time.sleep(PAUZA)
        if i % 50 == 0:
            print(f"  {i}/{len(knihy)}", file=sys.stderr)
    json.dump(out, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def hledat(obec):
    q = norm(obec)
    hits = [k for k in index() if any(q in norm(o) for o in k["obce"]) or q in norm(k["nazev"])]
    if not hits:
        print(f"„{obec}“ v popisech knih není. Popisy obcí v ARONu nejsou úplné: zkus panství, kam obec tehdy patřila,"
              " německé jméno nebo sousední větší obec (a pak obec hledej na snímcích knihy).")
    for k in hits:
        print(f'{k["id"]} | {k["nazev"]} | {k["roky"]} | sign. {k["signatura"]} | {k["snimku"]} sn. | obce: {", ".join(k["obce"])}')


def soubory(apu_id):
    """pracovni/aron_paths/<apu>.txt – adresy snímků (.dzi na obrázkovém serveru MZA), jedna na řádek, pro aron_obrazovka.sh."""
    k = kniha(apu_id)
    d = os.path.join(ROOT, "pracovni", "aron_paths"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, apu_id + ".txt")
    radky = "\n".join(k["dzi"]) + "\n"
    if not os.path.exists(p) or open(p).read() != radky:
        open(p, "w").write(radky)
    return k


def link(apu_id, n):
    k = kniha(apu_id)
    return f'https://www.mza.cz/aron/apu/{apu_id}/dao/{apu_id}/file/{k["soubory"][int(n) - 1]}'


def svazek(apu_id):
    k = kniha(apu_id)
    data = {"archiv": "Moravský zemský archiv v Brně – fond D 1 Lánové rejstříky", "portal": "ARON (MZA)",
            "svazek": f'{k["nazev"]}, sign. {k["signatura"]} ({k["roky"]})',
            "popis": f'lánový rejstřík; obce v popisu: {", ".join(k["obce"])}; {len(k["soubory"])} snímků',
            "url": f"https://www.mza.cz/aron/apu/{apu_id}"}
    tmp = os.path.join(ROOT, "pracovni", f"svazek_lr{apu_id[:6]}.json")
    json.dump(data, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
    subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "zapis.py"), "svazky", "lr" + apu_id[:6], tmp], check=True)
    os.remove(tmp)


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "hledat" and len(a) > 1:
        hledat(a[1])
    elif cmd == "index":
        print(len(index("--obnovit" in a)), "knih v indexu")
    elif cmd == "info" and len(a) > 1:
        k = kniha(a[1])
        print(f'{k["nazev"]} | {k["roky"]} | sign. {k["signatura"]} | {len(k["soubory"])} snímků | obce: {", ".join(k["obce"])}')
    elif cmd == "snimek" and len(a) >= 4:
        soubory(a[1])
        sys.exit(subprocess.run(["zsh", os.path.join(ROOT, "tools", "aron_obrazovka.sh"), a[1], a[2], a[3], *a[4:5]]).returncode)
    elif cmd == "link" and len(a) > 2:
        print(link(a[1], a[2]))
    elif cmd == "svazek" and len(a) > 1:
        svazek(a[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
