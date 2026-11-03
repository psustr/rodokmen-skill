#!/usr/bin/env python3
"""Matriky MZA Brno (Acta Publica) bez prohlížeče.

Použití:
  mza.py prevod <starý odkaz actapublica.eu>     → nový odkaz www.mza.cz/actapublica (oficiální převodník)
  mza.py hledat "Obec"                           → knihy obce: id | č. knihy | původce (fara) | roky N/O/Z (index v závorce) | snímků
  mza.py info <odkaz nebo id knihy>              → číslo knihy, původce, roky, části a počet snímků
  mza.py snimek <odkaz s ?image=…> <out.jpg> [-1]
  mza.py snimek <id knihy> <pořadí snímku> <out.jpg> [-1]
                                                 → složí snímek z dlaždic (Deep Zoom); -1 = poloviční rozlišení
Starý odkaz lze rovnou dát i do `info` a `snimek` (převede se sám).
Pozor: id v starých odkazech actapublica.eu NENÍ id v nových odkazech – vždy převádět.
Stahuje přes curl (Python urllib server odmítá). Snímky šetrně – jeden po druhém, už stažené nestahuj znovu.
"""
import time, html, os, re, subprocess, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://www.mza.cz/actapublica/matrika/detail/"
IIP = "https://www.mza.cz/iipsrv/iipsrv.fcgi?Deepzoom="
UA = ["-A", "Mozilla/5.0", "-e", "https://www.mza.cz/actapublica/"]


def curl(url, out=None, params=None):
    cmd = ["curl", "-sSL", "--fail", *UA]
    if params:
        cmd += ["-G", url] + sum([["--data-urlencode", f"{k}={v}"] for k, v in params.items()], [])
    else:
        cmd.append(url)
    if out:
        subprocess.run(cmd + ["-o", out], check=True)
        return None
    return subprocess.run(cmd, check=True, capture_output=True).stdout.decode("utf-8", "replace")


def prevod(old):
    t = curl("https://www.mza.cz/actapublica/matrika/prevodnik", params={"old_link": old})
    m = re.search(r'https://www\.mza\.cz/actapublica/matrika/detail/\d+\?image=[^"<&\s]+', t)
    if not m:
        sys.exit(f"Převodník odkaz nezná: {old}")
    return m.group(0)


def url_of(x):
    if "actapublica.eu" in x:
        return prevod(x)
    return x if x.startswith("http") else BASE + x


CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pracovni", "mza_paths")


def page(url):
    """HTML stránky knihy a seznam snímků. Od 11/2026 MZA chrání stránky ověřením (altcha) a obrázky podepsanými
    adresami (…/iip-srv/iipsrv.fcgi/<platnost>/<podpis>?Deepzoom=…). Když curl dostane jen ověřovací bránu,
    vezmou se adresy z mezipaměti pracovni/mza_paths/<id>.txt, kterou naplní `tools/mza_safari.sh <id>` z prohlížeče."""
    t = curl(url).replace("\\/", "/")
    paths = []
    for p in re.findall(r'(iip-srv/iipsrv\.fcgi/\d+/[^?"]+\?Deepzoom=[^"]+?\.jp2)\.dzi', t):
        p = "https://www.mza.cz/" + p
        if p not in paths:
            paths.append(p)
    if not paths:
        for p in re.findall(r'Deepzoom=([^"]+?\.jp2)\.dzi', t):
            if p not in paths:
                paths.append(p)
    if not paths:
        m = re.search(r"detail/(\d+)", url)
        f = os.path.join(CACHE, m.group(1) + ".txt") if m else ""
        if f and os.path.exists(f):
            paths = [x.strip() for x in open(f, encoding="utf-8") if x.strip()]
            exp = re.search(r"iipsrv\.fcgi/(\d+)/", paths[0] if paths else "")
            if exp and int(exp.group(1)) < time.time():
                sys.exit(f"Podepsané adresy snímků knihy {m.group(1)} vypršely – obnov je: tools/mza_safari.sh {m.group(1)}")
        else:
            sys.exit("MZA vrátila ověření „nejste robot“ místo knihy. Ověření projde v prohlížeči projektu (pracovni/prohlizec.txt: "
                     f"Safari / Google Chrome, JavaScript z událostí Apple povolen) – spusť: tools/mza_safari.sh {m.group(1) if m else '<id>'}")
    return t, paths


def info(x):
    url = url_of(x)
    t, paths = page(url)
    txt = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    txt = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt)))
    m = re.search(r"Základní údaje(.*?)Provozovatel", txt)
    print(url)
    print((m.group(1) if m else txt[:2000]).strip())
    print(f"Snímků: {len(paths)}")
    im = re.search(r"image=([^&]+)", url)
    if im:
        n = next((i for i, p in enumerate(paths, 1) if p.endswith(im.group(1))), None)
        print(f"Odkaz míří na snímek č. {n}")


def hledat(obec):
    """Vypíše knihy obce: id | č. knihy | původce | narození | oddaní | zemřelí | snímků."""
    pg = 1
    while True:
        t = curl("https://www.mza.cz/actapublica/matrika/hledani_obec",
                 params={"typ": "obec", "search_by_obec": obec, "page": pg})
        rows = re.findall(r"<tr.*?</tr>", t, re.S)[1:]
        for r in rows:
            m = re.search(r"matrika/detail/(\d+)", r)
            if not m:
                continue
            r = re.sub(r'(data-content|title)="[^"]*"', "", r)
            cells = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c))).strip()
                     for c in re.findall(r"<td.*?</td>", r, re.S)]
            kn, puv, nar, odd, zem, _, sn = (cells + [""] * 8)[:7]
            puv = puv.replace(" římskokatolická církev", "")
            print(f"{m.group(1)} | kn. {kn} | {puv} | N {nar} | O {odd} | Z {zem} | {sn} sn.")
        if f"page={pg + 1}" not in t:
            break
        pg += 1


def snimek(path, out, half=False):
    base = path if path.startswith("http") else IIP + path
    dzi = curl(base + ".dzi")
    w, h = map(int, re.search(r'Width="(\d+)" Height="(\d+)"', dzi).groups())
    ts = int(re.search(r'TileSize="(\d+)"', dzi).group(1))
    level = max(w, h).bit_length() if max(w, h) & (max(w, h) - 1) else max(w, h).bit_length() - 1
    if half:
        level -= 1
        w, h = (w + 1) // 2, (h + 1) // 2
    cols, rows = -(-w // ts), -(-h // ts)
    with tempfile.TemporaryDirectory() as d:
        cfg = os.path.join(d, "cfg")
        with open(cfg, "w") as f:
            for y in range(rows):
                for x in range(cols):
                    f.write(f'url = "{base}_files/{level}/{x}_{y}.jpg"\noutput = "{d}/{y:03d}_{x:03d}.jpg"\n')
        subprocess.run(["curl", "-sS", "--fail", "-Z", "--parallel-max", "4", *UA, "-K", cfg], check=True)
        rowimgs = []
        for y in range(rows):
            r = f"{d}/row{y:03d}.png"
            subprocess.run(["magick", *[f"{d}/{y:03d}_{x:03d}.jpg" for x in range(cols)], "+append", r], check=True)
            rowimgs.append(r)
        subprocess.run(["magick", *rowimgs, "-append", "-quality", "92", out], check=True)
    print(f"{out}: {w}×{h} px")


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "prevod":
        print(prevod(a[1]))
    elif cmd == "hledat":
        hledat(a[1])
    elif cmd == "info":
        info(a[1])
    elif cmd == "snimek":
        half = "-1" in a
        a = [x for x in a if x != "-1"]
        url = url_of(a[1])
        _, paths = page(url)
        if len(a) == 3:
            m = re.search(r"image=([^&]+)", url)
            path = next(p for p in paths if p.endswith(m.group(1)))
            out = a[2]
        else:
            path, out = paths[int(a[2]) - 1], a[3]
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        snimek(path, out, half)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
