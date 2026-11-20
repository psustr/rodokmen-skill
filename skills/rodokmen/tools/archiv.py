#!/usr/bin/env python3
"""Sdílený archiv stažených snímků – pro všechny rodokmeny a sezení na tomto počítači.

Každý stažený snímek se ukládá i do společné složky (výchozí ~/Work/rodokmen-archiv, jinak proměnná prostředí
RODOKMEN_ARCHIV), aby ho jiný projekt nebo jiné sezení nemuselo stahovat znovu a archiv se zbytečně nezatěžoval.
Na stejném disku se ukládá pevným odkazem (hard link) – místo na disku zabere jen jednou.

Použití (z kořene projektu: python3 -I tools/archiv.py …):
  najdi <portál> <kniha> <snímek> [varianta]   vypíše cestu k uloženému snímku (kód 1 = není)
  vydej <portál> <kniha> <snímek> <out.jpg> [varianta] [x0,y0,x1,y1]
                         zkopíruje uložený snímek do out.jpg; výřez / náhled udělá z celého snímku na místě
                         (kód 0 = hotovo bez sítě, 1 = v archivu není – stahuj); --presne = jen přesně tato
                         varianta (pro přiblížení v prohlížeči, které má vyšší rozlišení než výřez z celého snímku)
  uloz <portál> <kniha> <snímek> <soubor.jpg> [varianta] [--popis "…"]
                         uloží snímek do archivu a zapíše ho do indexu (po každém stažení)
  hledej <text>          řádky indexu, které obsahují text (portál, kniha, popis, projekt…)
  prehled                kolik snímků a místa archiv zabírá, po portálech
  pripomen               připomínka úklidu (jednou za 14 dní, nebo když archiv přeroste 20 GB)
  uklizeno               zapíše, že uživatel archiv prošel / promazal (připomínka se odloží)
  import <projekt>       jednorázově zařadí snímky, které už v projektu leží (pracovni/), podle názvů souborů
  reindex                znovu sestaví index ze souborů v archivu

Portál = krátký název zdroje: mza (Acta Publica, kniha = číslo matriky), aron (ARON MZA, kniha = apu), pf (Porta
fontium, kniha = např. cachrov-10), opava (ZA Opava), trebon, ebadatelna, ahmp … Snímek = pořadí snímku v knize.
Varianta: prázdná = celý snímek v plném (nebo nejlepším dostupném) rozlišení; „nahled“ = zmenšený; „pul“ = poloviční;
„x0,y0,x1,y1“ = výřez. Do archivu ukládej hlavně celé snímky – výřezy z nich nástroj udělá sám.
Složky: snimky/<portál>/<kniha>/<snímek>[_<varianta>].jpg; index.tsv; projekty/<projekt>/… (importované soubory,
u kterých nešlo poznat knihu a snímek – jen dohledatelné podle názvu).
"""
import csv, datetime, hashlib, json, os, re, shutil, subprocess, sys
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

A = os.path.expanduser(os.environ.get("RODOKMEN_ARCHIV", "~/Work/rodokmen-archiv"))
IDX = os.path.join(A, "index.tsv")
STAV = os.path.join(A, ".pripominka.json")
POLE = ["portal", "kniha", "snimek", "varianta", "soubor", "kb", "rozmer", "datum", "projekt", "popis"]
PRIPOMEN_DNI, PRIPOMEN_GB = 14, 20


def var_jmeno(v):
    v = (v or "").strip()
    return v.replace(",", "-") if v else ""


def cesta(portal, kniha, snimek, varianta=""):
    v = var_jmeno(varianta)
    return os.path.join(A, "snimky", portal, str(kniha), f"{snimek}{'_' + v if v else ''}.jpg")


def rozmer(p):
    try:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", p], capture_output=True, text=True).stdout
        w, h = re.findall(r"pixel(?:Width|Height): (\d+)", out)
        return f"{w}x{h}"
    except Exception:
        try:
            out = subprocess.run(["magick", "identify", "-format", "%wx%h", p], capture_output=True, text=True).stdout
            return out.strip()
        except Exception:
            return ""


def nacti():
    if not os.path.exists(IDX):
        return []
    with open(IDX, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def zapis(rows):
    os.makedirs(A, exist_ok=True)
    tmp = IDX + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, POLE, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["portal"], r["kniha"], int(r["snimek"]) if str(r["snimek"]).isdigit() else 0, r["varianta"])):
            w.writerow(r)
    os.replace(tmp, IDX)


def projekt():
    return os.path.basename(os.getcwd())


def link(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        if os.path.samefile(src, dst):
            return False
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)
    return True


def uloz(portal, kniha, snimek, soubor, varianta="", popis="", rows=None, ulozit=True):
    if not os.path.exists(soubor) or os.path.getsize(soubor) < 1000:
        sys.exit(f"archiv: soubor {soubor} není nebo je prázdný")
    dst = cesta(portal, kniha, snimek, varianta)
    link(os.path.abspath(soubor), dst)
    rows = nacti() if rows is None else rows
    rel = os.path.relpath(dst, A)
    rows[:] = [r for r in rows if r["soubor"] != rel]
    rows.append(dict(portal=portal, kniha=str(kniha), snimek=str(snimek), varianta=var_jmeno(varianta), soubor=rel,
                     kb=str(os.path.getsize(dst) // 1024), rozmer=rozmer(dst), datum=datetime.date.today().isoformat(),
                     projekt=projekt(), popis=popis))
    if ulozit:
        zapis(rows)
    return dst


def najdi(portal, kniha, snimek, varianta=""):
    p = cesta(portal, kniha, snimek, varianta)
    if os.path.exists(p):
        return p
    if not varianta:   # celý snímek: vezmi i „pul“ (poloviční rozlišení), když jiný není
        q = cesta(portal, kniha, snimek, "pul")
        if os.path.exists(q):
            return q
    return None


def vydej(portal, kniha, snimek, out, varianta="", crop=None, presne=False):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    presne_ = najdi(portal, kniha, snimek, ",".join(f"{v:g}" for v in crop) if crop else varianta)
    src = presne_ or (None if presne else najdi(portal, kniha, snimek) if (crop or varianta == "nahled") else None)
    if not src:
        return 1
    if presne_:
        shutil.copyfile(src, out)
    else:   # výřez nebo náhled z celého snímku – bez sítě
        args = ["magick", src]
        if crop:
            x0, y0, x1, y1 = crop
            wh = rozmer(src).split("x")
            W, H = int(wh[0]), int(wh[1])
            args += ["-crop", f"{int((x1 - x0) * W)}x{int((y1 - y0) * H)}+{int(x0 * W)}+{int(y0 * H)}", "+repage"]
        if varianta == "nahled":
            args += ["-resize", "25%"]
        args += ["-quality", "92", out]
        subprocess.run(args, check=True)
    print(f"{out} (z archivu {os.path.relpath(src, A)}, bez stahování)")
    return 0


def velikost():
    tot, po = 0, {}
    seen = set()
    for root, _, files in os.walk(A):
        for fn in files:
            p = os.path.join(root, fn)
            st = os.stat(p)
            if st.st_ino in seen:
                continue
            seen.add(st.st_ino)
            tot += st.st_size
            rel = os.path.relpath(p, A).split(os.sep)
            k = "/".join(rel[:2]) if rel[0] in ("snimky", "projekty") and len(rel) > 2 else rel[0]
            po[k] = po.get(k, 0) + st.st_size
    return tot, po


def prehled():
    rows = nacti()
    tot, po = velikost()
    print(f"Archiv {A}: {len(rows)} snímků v indexu, {tot / 2**30:.1f} GB")
    for k, v in sorted(po.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v / 2**20:.0f} MB")


def pripomen(vynutit=False):
    st = json.load(open(STAV)) if os.path.exists(STAV) else {}
    dnes = datetime.date.today()
    posl = datetime.date.fromisoformat(st.get("pripomenuto", "2000-01-01"))
    tot, _ = velikost()
    if vynutit or (dnes - posl).days >= PRIPOMEN_DNI or tot > PRIPOMEN_GB * 2**30:
        print(f"PŘIPOMEŇ UŽIVATELI: sdílený archiv snímků {A} zabírá {tot / 2**30:.1f} GB "
              f"(naposledy uklizeno {st.get('uklizeno', 'nikdy')}). Ať ho občas projde a promaže snímky, které už "
              f"nepotřebuje (pracovní výřezy, prošlé knihy bez nálezu); výřezy použité na webu jsou v projektu "
              f"(vyrezy/, zdroje/), ty archiv nepotřebují. Po úklidu: archiv.py uklizeno.")
        st["pripomenuto"] = dnes.isoformat()
        os.makedirs(A, exist_ok=True)
        json.dump(st, open(STAV, "w"))


def uklizeno():
    st = json.load(open(STAV)) if os.path.exists(STAV) else {}
    st["uklizeno"] = st["pripomenuto"] = datetime.date.today().isoformat()
    os.makedirs(A, exist_ok=True)
    json.dump(st, open(STAV, "w"))
    reindex()


# --- import už stažených souborů podle názvů ------------------------------------------------------------------
PF = re.compile(r"(?:^|/)(?:pf_)?([a-z][a-z-]+-\d{2})_(\d{1,4})(?:_(n|nahled|0|1|full|[0-9.]+-[0-9.]+-[0-9.]+-[0-9.]+))?\.jpg$")
MZA = re.compile(r"(?:^|/)n?([3-9]\d{3}|1\d{4})_(\d{1,4})(?:_(pul|a|b|w|l|full|0|1))?\.jpg$")
ARON_DIR = re.compile(r"lanove-rejstriky/[^/]+/(\d+)\.jpg$")


def zarad(rel, projekt_jm):
    """(portál, kniha, snímek, varianta) z cesty souboru, nebo None."""
    m = PF.search(rel)
    if m:
        v = {"n": "nahled", "nahled": "nahled", "1": "pul", "0": "", "full": "", None: ""}.get(m.group(3), m.group(3))
        return ("pf", m.group(1), int(m.group(2)), v)
    m = MZA.search(rel)
    if m and "/tmp/" not in rel:
        v = {"pul": "pul", None: "", "full": "", "0": "", "1": "pul"}.get(m.group(3))
        if v is None:   # a/b/w/l = výřezy (levá/pravá…) – nechej v projektech
            return None
        return ("mza", m.group(1), int(m.group(2)), v)
    return None


def import_(proj):
    root = os.path.abspath(proj)
    jm = os.path.basename(root)
    rows = nacti()
    mam = {os.stat(os.path.join(A, r["soubor"])).st_ino for r in rows if os.path.exists(os.path.join(A, r["soubor"]))}
    n_kat = n_proj = 0
    for base in ("pracovni",):
        for dp, dn, files in os.walk(os.path.join(root, base)):
            dn[:] = [d for d in dn if not d.startswith(".")]
            for fn in files:
                if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                p = os.path.join(dp, fn)
                if os.path.islink(p):
                    continue
                st = os.stat(p)
                if st.st_size < 40_000 or st.st_ino in mam:   # dlaždice a miniatury vynech
                    continue
                rel = os.path.relpath(p, root)
                z = zarad(rel, jm)
                if z:
                    dst = cesta(z[0], z[1], z[2], z[3])
                    if os.path.exists(dst) and os.path.getsize(dst) >= st.st_size:
                        continue
                    uloz(z[0], z[1], z[2], p, z[3], popis=f"import {jm}/{rel}", rows=rows, ulozit=False)
                    n_kat += 1
                else:
                    dst = os.path.join(A, "projekty", jm, rel)
                    if link(p, dst):
                        n_proj += 1
                mam.add(st.st_ino)
    zapis(rows)
    seznam_projektu()
    print(f"import {jm}: {n_kat} snímků zařazeno podle knihy, {n_proj} dalších souborů v projekty/{jm}/")


def seznam_projektu():
    """projekty/SEZNAM.tsv – všechny importované soubory, které nešlo zařadit (hledání podle názvu)."""
    d = os.path.join(A, "projekty")
    if not os.path.isdir(d):
        return
    with open(os.path.join(d, "SEZNAM.tsv"), "w", encoding="utf-8") as f:
        f.write("soubor\tkb\n")
        for dp, _, files in os.walk(d):
            for fn in sorted(files):
                if fn.endswith(".jpg") or fn.endswith(".png"):
                    p = os.path.join(dp, fn)
                    f.write(f"{os.path.relpath(p, d)}\t{os.path.getsize(p) // 1024}\n")


def reindex():
    stare = {r["soubor"]: r for r in nacti()}
    rows = []
    sd = os.path.join(A, "snimky")
    for dp, _, files in os.walk(sd):
        for fn in files:
            m = re.match(r"(\d+)(?:_(.+))?\.jpg$", fn)
            if not m:
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, A)
            portal, kniha = os.path.relpath(dp, sd).split(os.sep, 1)
            r = stare.get(rel) or dict(portal=portal, kniha=kniha, snimek=m.group(1), varianta=m.group(2) or "", soubor=rel,
                                       datum="", projekt="", popis="")
            r["kb"], r["rozmer"] = str(os.path.getsize(p) // 1024), r.get("rozmer") or rozmer(p)
            rows.append(r)
    zapis(rows)
    seznam_projektu()
    print(f"index: {len(rows)} snímků")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    c = a[0]
    if c == "najdi" and len(a) >= 4:
        p = najdi(a[1], a[2], a[3], a[4] if len(a) > 4 else "")
        print(p or "")
        sys.exit(0 if p else 1)
    if c == "vydej" and len(a) >= 5:
        var, crop = "", None
        for x in a[5:]:
            if x == "--presne":
                continue
            if x.count(",") == 3:
                crop = tuple(float(v) for v in x.split(","))
            else:
                var = x
        sys.exit(vydej(a[1], a[2], a[3], a[4], var, crop, "--presne" in a))
    if c == "uloz" and len(a) >= 5:
        popis, rest = "", []
        it = iter(a[5:])
        for x in it:
            if x == "--popis":
                popis = next(it, "")
            else:
                rest.append(x)
        print(uloz(a[1], a[2], a[3], a[4], rest[0] if rest else "", popis))
        return
    if c == "hledej" and len(a) > 1:
        q = a[1].lower()
        for r in nacti():
            if q in "\t".join(r.values()).lower():
                print("\t".join(r[k] for k in POLE))
        return
    if c == "prehled":
        return prehled()
    if c == "pripomen":
        return pripomen("--ted" in a)
    if c == "uklizeno":
        return uklizeno()
    if c == "import" and len(a) > 1:
        return import_(a[1])
    if c == "reindex":
        return reindex()
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
