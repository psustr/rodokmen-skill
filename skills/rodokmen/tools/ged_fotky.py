#!/usr/bin/env python3
"""Fotky z rodinného stromu (export GEDCOM z Geni, MyHeritage…) – přehled a stažení vybraných.

Použití (z kořene projektu):
  ged_fotky.py <export.ged> <ID výchozí osoby v GEDCOM> seznam
      → kdo má v exportu fotky: ID | jméno | narození | † | počet | Kekulé (je-li předkem) | nejbližší předek a cesta
        (otec/matka/sourozenec/manžel/ka/dítě). Snímky matrik (soubory pojmenované číslem, např. „5694_original.png“)
        a ikony vynechá – na webu jsou zápisy v lepší kvalitě.
  ged_fotky.py <export.ged> <ID výchozí osoby> stahni <ID> [<ID> …]
      → stáhne fotky vybraných osob do pracovni/ged_foto/<ID>_<n>.<přípona> (po jedné, pauza 3 s).

Odkazy na fotky jsou přímo v exportu (řádky „2 FILE https://…“, podepsané – platí jen nějakou dobu, pak nový export).
Nic se neprochází ani nestahuje hromadně z webu služby: jen soubory, na které odkazuje uživatelův vlastní export.
Soukromí: fotky žijících jen se souhlasem (děti se souhlasem rodičů) – viz reference/web.md (Portréty a fotografie).
"""
import collections, os, re, subprocess, sys, time
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

UA = "rodokmen-skill (+https://github.com/psustr/rodokmen-skill)"
SCAN = re.compile(r"/\d+_original\.(png|jpe?g)", re.I)   # snímky matrik pojmenované číslem knihy


def load(path):
    I, F = {}, {}
    for r in open(path, encoding="utf-8", errors="replace").read().split("\n0 "):
        head = r.split("\n")[0].split()
        if len(head) < 2:
            continue
        i = head[0].strip("@")
        if head[1] == "INDI":
            n = re.search(r"1 NAME (.*)", r)
            b = re.search(r"1 BIRT\n2 DATE (.*)", r)
            d = re.search(r"\n1 DEAT(?:\n2 DATE (.*))?", r)
            I[i] = dict(n=n.group(1).replace("/", "").strip() if n else "?", b=b.group(1) if b else "",
                        dead=bool(d), dd=(d.group(1) or "") if d else "",
                        famc=[x.strip("@") for x in re.findall(r"1 FAMC (\S+)", r)],
                        fams=[x.strip("@") for x in re.findall(r"1 FAMS (\S+)", r)],
                        files=[f for f in re.findall(r"2 FILE (\S+)", r) if not SCAN.search(f)])
        elif head[1] == "FAM":
            g = lambda t: (re.search(rf"1 {t} (\S+)", r) or [0, ""])[1].strip("@")
            F[i] = dict(h=g("HUSB"), w=g("WIFE"), c=[x.strip("@") for x in re.findall(r"1 CHIL (\S+)", r)])
    return I, F


def kekule(I, F, root):
    kek, todo = {root: 1}, [root]
    while todo:
        x = todo.pop()
        for f in I[x]["famc"]:
            fa = F.get(f, {})
            for p, k in ((fa.get("h"), 2 * kek[x]), (fa.get("w"), 2 * kek[x] + 1)):
                if p in I and p not in kek:
                    kek[p] = k
                    todo.append(p)
    return kek


def neighbours(I, F, x):
    for f in I[x]["famc"]:
        fa = F.get(f, {})
        for p, rel in ((fa.get("h"), "otec"), (fa.get("w"), "matka")):
            if p in I:
                yield p, rel
        for c in fa.get("c", []):
            if c != x and c in I:
                yield c, "sourozenec"
    for f in I[x]["fams"]:
        fa = F.get(f, {})
        for p in (fa.get("h"), fa.get("w")):
            if p and p != x and p in I:
                yield p, "manžel/ka"
        for c in fa.get("c", []):
            if c in I:
                yield c, "dítě"


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.exit(__doc__)
    I, F = load(a[0])
    root = a[1].strip("@")
    if root not in I:
        sys.exit(f"ID {root} v exportu není (ID osob jsou na řádcích „0 @I…@ INDI“)")
    kek = kekule(I, F, root)
    if a[2] == "seznam":
        for i, p in I.items():
            if not p["files"]:
                continue
            seen, dq, found = {i: None}, collections.deque([i]), None
            while dq:
                x = dq.popleft()
                if x in kek and x != i or x == i and i in kek:
                    found = x
                    break
                for y, rel in neighbours(I, F, x):
                    if y not in seen:
                        seen[y] = (x, rel)
                        dq.append(y)
            path, y = [], found
            while y and seen.get(y):
                x, rel = seen[y]
                path.append(rel)
                y = x
            near = f"č. {kek[found]} {I[found]['n']}" if found else "–"
            print(f"{i}\t{p['n']}\t{p['b']}\t{'† ' + p['dd'] if p['dead'] else 'žije?'}\t{len(p['files'])}\t"
                  f"{kek.get(i, '')}\t{near}\t{' → '.join(path)}")
    elif a[2] == "stahni":
        out_dir = os.path.join("pracovni", "ged_foto")
        os.makedirs(out_dir, exist_ok=True)
        for i in a[3:]:
            i = i.strip("@")
            for n, url in enumerate(I.get(i, {}).get("files", []), 1):
                ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
                out = os.path.join(out_dir, f"{i}_{n}{ext}")
                if not os.path.exists(out):
                    subprocess.run(["curl", "-sS", "--fail", "-A", UA, "-o", out, url])
                    time.sleep(3)
                print(out if os.path.exists(out) else f"CHYBA {i} {n} (odkaz vypršel? udělej nový export)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
