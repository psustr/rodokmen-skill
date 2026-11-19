#!/usr/bin/env python3
"""omez.py – společný omezovač rychlosti pro všechny síťové požadavky skillu rodokmen.

Každý nástroj, skript i curl, který sahá na internet, se spouští PŘES TENTO OMEZOVAČ (z kořene projektu):

  python3 -I SKILL_DIR/omezovac/omez.py tools/aron_search.py "Obec"        # nástroj v Pythonu
  python3 -I SKILL_DIR/omezovac/omez.py tools/mza_obrazovka.sh 6105 97 x.jpg # skript (bash/zsh)
  python3 -I SKILL_DIR/omezovac/omez.py curl -sS -o x.html https://…         # samotný curl
  python3 -I SKILL_DIR/omezovac/omez.py python -c "import urllib.request; …" # jednorázový kód v Pythonu
  python3 -I SKILL_DIR/omezovac/omez.py web mza.cz -- osascript …           # jiný příkaz pro daný web (1 stránka)
  python3 -I SKILL_DIR/omezovac/omez.py stav                                 # zablokované weby a fronty

Pravidla (platí pro každý web zvlášť; web = doména 2. řádu, např. mza.cz, archives.cz):
  * vyhledávání, API a HTML stránky: nejvýš 1 požadavek za 2 s,
  * dlaždice a obrázky skenů: nejvýš 5 požadavků za 1 s,
  * když web vrátí HTTP 429 nebo 503: web je na 30 minut zablokovaný, nástroj se hned ukončí (kód 75)
    a požadavek se neopakuje. Během blokace omezovač žádný požadavek na ten web nepustí.
Stav sdílí přes soubory v ~/.cache/rodokmen-omezovac (RODOKMEN_OMEZOVAC_DIR) se zámkem, takže platí pro všechny
současně běžící procesy, projekty i pomocníky (subagenty).

Jak to funguje (soubory v tools/ se nemění):
  * Python: nástroj běží v podprocesu, kde je obalené http.client (putrequest/getresponse) – tím jde každý
    požadavek urllib/http.client; před odesláním čeká na volný čas, po odpovědi kontroluje 429/503.
  * curl: v PATH podprocesu je omezovac/bin/curl, který volá `omez.py curl`: počítá adresy (i v -K souboru),
    vyhradí si časy ve sdílené frontě, předá curlu --rate, odstraní --retry* a -Z/--parallel (curl by jinak
    429/503 sám opakoval a --rate by neplatil) a z --write-out přečte stavové kódy.
  * Skripty, které ovládají prohlížeč (mza_obrazovka.sh, aron_obrazovka.sh, …): omezovač před spuštěním zkontroluje
    blokaci a započítá jeden požadavek „stránka“ na web. Dlaždice, které si pak stahuje sám prohlížeč, omezovač
    nevidí – proto tyto skripty mají vlastní zámek a pauzu (jeden snímek najednou).
Kód 75 = web zablokovaný (EX_TEMPFAIL): nástroj ukonči, neopakuj, řekni uživateli a jdi na jinou práci.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse

INTERVAL = {"stranka": 2.0, "dlazdice": 0.2}      # 1 požadavek / 2 s; 5 požadavků / 1 s
CURL_RATE = {"stranka": "30/m", "dlazdice": "5/s"}
BLOK_S = 30 * 60
KOD_BLOK = 75
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "bin")
STAV = os.environ.get("RODOKMEN_OMEZOVAC_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "rodokmen-omezovac")
# skripty, které ovládají prohlížeč: web, na který prohlížeč půjde (požadavky stránky započítá omezovač předem)
PROHLIZEC = {"mza_obrazovka.sh": "mza.cz", "mza_safari.sh": "mza.cz", "mza_snimek.sh": "mza.cz",
             "aron_obrazovka.sh": "mza.cz", "opava_safari.sh": "archives.cz"}
DVOUDILNE = {"co.uk", "org.uk", "ac.uk", "gv.at", "ac.at", "or.at", "co.at", "com.pl", "gov.pl", "org.pl",
             "com.au", "co.nz", "com.br"}
DLAZDICE = re.compile(r"(\.(jpe?g|png|gif|webp|tiff?|jp2|j2k|bmp)$|/iipsrv|[?&](deepzoom|fif|iiif|jtl|cvt)=|_files/\d+/"
                      r"|/tilegroup\d+/|/zoomify/.+\.jpe?g|/iiif/.+/(full|max|\d+,\d+,\d+,\d+)/|/tiles?/|/thumbnails?/"
                      r"|/iipimage/|/ximage/.+\.(jpe?g|png)|/dao/[^/]+/file/)",
                      re.I)


# ---------- sdílený stav ----------
def web(host):
    """Klíč webu pro limit: doména 2. řádu (www.mza.cz → mza.cz). localhost a IP adresy se neomezují (None)."""
    if not host:
        return None
    host = host.strip("[]").lower().rstrip(".")
    if host in ("localhost",) or re.fullmatch(r"[\d.]+|[0-9a-f:]+", host):
        return "localhost" if os.environ.get("RODOKMEN_OMEZOVAC_TEST") else None   # jen pro testy omezovače
    parts = host.split(".")
    n = 3 if ".".join(parts[-2:]) in DVOUDILNE else 2
    return ".".join(parts[-n:])


def druh(url):
    path = urllib.parse.urlsplit(url)
    return "dlazdice" if DLAZDICE.search(path.path + ("?" + path.query if path.query else "")) else "stranka"


class _Zamek:
    def __init__(self, klic):
        os.makedirs(STAV, exist_ok=True)
        self.path = os.path.join(STAV, klic + ".lock")

    def __enter__(self):
        self.f = open(self.path, "a+")
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    self.f.seek(0)
                    msvcrt.locking(self.f.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl
            fcntl.flock(self.f.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        if os.name == "nt":
            import msvcrt
            self.f.seek(0)
            msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        self.f.close()


def _cti(klic):
    try:
        with open(os.path.join(STAV, klic + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _zapis(klic, st):
    p = os.path.join(STAV, klic + ".json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(st, f)
    os.replace(p + ".tmp", p)


def _log(text):
    os.makedirs(STAV, exist_ok=True)
    with open(os.path.join(STAV, "zaznam.log"), "a", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")


def blokace(klic):
    """(do kdy, důvod), pokud je web právě zablokovaný, jinak None."""
    st = _cti(klic)
    if st.get("blok_do", 0) > time.time():
        return st["blok_do"], st.get("duvod", "")
    return None


class Zablokovano(Exception):
    pass


def _hlaska_blok(klic, do, duvod):
    return (f"omezovač: web {klic} je zablokovaný do {time.strftime('%H:%M', time.localtime(do))} ({duvod}). "
            "Požadavek neodeslán – nástroj končí. Neopakuj ho, řekni to uživateli a dělej mezitím jinou práci.")


def vyhrad(klic, kind, n=1):
    """Vyhradí n po sobě jdoucích časů pro web a druh požadavku; vrátí čas prvního (a počká na něj, je-li sam=True)."""
    with _Zamek(klic):
        st = _cti(klic)
        now = time.time()
        if st.get("blok_do", 0) > now:
            raise Zablokovano(_hlaska_blok(klic, st["blok_do"], st.get("duvod", "")))
        slot = max(now, st.get(kind, 0))
        st[kind] = slot + n * INTERVAL[kind]
        _zapis(klic, st)
    return slot


def pockej(url, n=1):
    klic = web(urllib.parse.urlsplit(url).hostname)
    if not klic:
        return
    slot = vyhrad(klic, druh(url), n)
    d = slot - time.time()
    if d > 0:
        time.sleep(d)


def zablokuj(klic, kod, url):
    with _Zamek(klic):
        st = _cti(klic)
        st["blok_do"] = time.time() + BLOK_S
        st["duvod"] = f"HTTP {kod} na {url[:150]}"
        _zapis(klic, st)
    _log(f"BLOKACE {klic} na {BLOK_S // 60} min: HTTP {kod} {url[:300]}")


def konec(zprava):
    """Ukončí celý nástroj (i rodiče a sourozence v jeho skupině procesů) – nic dalšího už neodejde."""
    sys.stderr.write("\n" + zprava + "\n")
    sys.stderr.flush()
    znacka = os.environ.get("OMEZ_ZNACKA")
    if znacka:
        try:
            with open(znacka, "w", encoding="utf-8") as f:
                f.write(zprava)
        except OSError:
            pass
    if znacka and os.name != "nt":   # jen pod dozorem omezovače (jinak bychom ukončili i shell uživatele)
        try:
            os.killpg(int(os.environ.get("OMEZ_PGID") or os.getpgrp()), signal.SIGTERM)
        except (OSError, ValueError):
            pass
    os._exit(KOD_BLOK)


# ---------- Python: obalení http.client ----------
def obal_http():
    import http.client
    put0, resp0 = http.client.HTTPConnection.putrequest, http.client.HTTPConnection.getresponse

    def putrequest(self, method, url, *a, **k):
        if "://" in url:
            full = url
        else:
            host = getattr(self, "_tunnel_host", None) or self.host
            port = getattr(self, "_tunnel_port", None) or self.port
            sch = "https" if isinstance(self, http.client.HTTPSConnection) else "http"
            full = f"{sch}://{host}" + ("" if port in (None, 80, 443) else f":{port}") + url
        self._omez_url = full
        try:
            pockej(full)
        except Zablokovano as e:
            konec(str(e))
        return put0(self, method, url, *a, **k)

    def getresponse(self, *a, **k):
        r = resp0(self, *a, **k)
        if r.status in (429, 503):
            url = getattr(self, "_omez_url", "")
            klic = web(urllib.parse.urlsplit(url).hostname)
            if klic:
                zablokuj(klic, r.status, url)
                konec(f"omezovač: {klic} vrátil HTTP {r.status} – web zablokován na 30 minut, nástroj ukončen "
                      "a požadavek se neopakuje.")
        return r

    http.client.HTTPConnection.putrequest = putrequest
    http.client.HTTPConnection.getresponse = getresponse


# ---------- curl ----------
S_ARG = set("AbcCdDeEFhHKmoQrTuUwxXyYz")           # krátké volby curl s argumentem
L_ARG = {"--abstract-unix-socket", "--cacert", "--capath", "--cert", "--cert-type", "--ciphers", "--config",
         "--connect-timeout", "--connect-to", "--continue-at", "--cookie", "--cookie-jar", "--data", "--data-ascii",
         "--data-binary", "--data-raw", "--data-urlencode", "--dns-servers", "--dump-header", "--expect100-timeout",
         "--form", "--form-string", "--header", "--interface", "--keepalive-time", "--key", "--limit-rate",
         "--local-port", "--max-filesize", "--max-redirs", "--max-time", "--noproxy", "--output", "--output-dir",
         "--parallel-max", "--pass", "--proxy", "--proxy-header", "--proxy-user", "--range", "--rate", "--referer",
         "--request", "--resolve", "--retry", "--retry-delay", "--retry-max-time", "--speed-limit", "--speed-time",
         "--time-cond", "--trace", "--trace-ascii", "--unix-socket", "--upload-file", "--url", "--url-query",
         "--user", "--user-agent", "--write-out", "--stderr", "--variable", "--json", "--aws-sigv4"}
ZAHOD_S_ARG = {"--retry", "--retry-delay", "--retry-max-time", "--parallel-max", "--rate"}
ZAHOD = {"--retry-all-errors", "--retry-connrefused", "--parallel", "--parallel-immediate", "-Z"}
ZNACKA = "@@OMEZ@@"


def _skutecny_curl():
    bin_n = os.path.normcase(os.path.realpath(BIN))
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or os.path.normcase(os.path.realpath(d)) == bin_n:
            continue
        for name in ("curl.exe", "curl") if os.name == "nt" else ("curl",):
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
    sys.exit("omezovač: skutečný curl nenalezen v PATH")


def _uprav_config(path, urls):
    """Přečte -K soubor: posbírá url, vyhodí retry/parallel/rate; vrátí cestu k upravené kopii."""
    out = []
    src = sys.stdin.read() if path == "-" else open(path, encoding="utf-8", errors="replace").read()
    for line in src.splitlines():
        s = line.strip()
        m = re.match(r"^-{0,2}([A-Za-z0-9-]+)\s*[=:]?\s*(.*)$", s)
        if m and not s.startswith("#"):
            key, val = m.group(1), m.group(2).strip().strip('"')
            if "--" + key in ZAHOD_S_ARG | ZAHOD or key in ("Z",):
                continue
            if key == "url":
                urls.append(val)
            elif re.match(r"^https?://", s.strip('"')):
                urls.append(s.strip('"'))
        out.append(line)
    fd, tmp = tempfile.mkstemp(prefix="omez_", suffix=".cfg")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return tmp


def curl(args):
    urls, out, wfmt, tmps = [], [], None, []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ZAHOD:
            i += 1
            continue
        if a.split("=", 1)[0] in ZAHOD_S_ARG:
            i += 1 if "=" in a else 2
            continue
        if a in ("-K", "--config") and i + 1 < len(args):
            tmp = _uprav_config(args[i + 1], urls)
            tmps.append(tmp)
            out += [a, tmp]
            i += 2
            continue
        if a in ("-w", "--write-out") and i + 1 < len(args):
            wfmt = args[i + 1]
            i += 2
            continue
        if a == "--url" and i + 1 < len(args):
            urls.append(args[i + 1])
            out += [a, args[i + 1]]
            i += 2
            continue
        if re.match(r"^-[A-Za-z]+$", a):            # spojené krátké volby (-sSLZ): Z pryč
            a = "-" + a[1:].replace("Z", "")
            if a == "-":
                i += 1
                continue
            out.append(a)
            if a[-1] in S_ARG and i + 1 < len(args):
                out.append(args[i + 1])
                i += 1
            i += 1
            continue
        if a in L_ARG and i + 1 < len(args):
            out += [a, args[i + 1]]
            i += 2
            continue
        if re.match(r"^(https?://)", a, re.I):
            urls.append(a)
        out.append(a)
        i += 1

    if urls:
        po_webech = {}
        for u in urls:
            klic = web(urllib.parse.urlsplit(u).hostname)
            if klic:
                d = po_webech.setdefault(klic, [0, "dlazdice"])
                d[0] += 1
                if druh(u) == "stranka":
                    d[1] = "stranka"
        try:
            for klic, (n, kind) in po_webech.items():     # nejdřív kontrola blokace všech webů
                b = blokace(klic)
                if b:
                    raise Zablokovano(_hlaska_blok(klic, *b))
            start = max([vyhrad(klic, kind, n) for klic, (n, kind) in po_webech.items()] or [time.time()])
        except Zablokovano as e:
            konec(str(e))
        if len(urls) > 1:
            kinds = {k for _, k in po_webech.values()}
            out = ["--rate", CURL_RATE["stranka" if "stranka" in kinds or not kinds else "dlazdice"]] + out
        d = start - time.time()
        if d > 0:
            time.sleep(d)
        out = ["-w", (wfmt or "") + "%{stderr}\n" + ZNACKA + " %{http_code} %{url}\n"] + out

    try:
        p = subprocess.run([_skutecny_curl()] + out, stderr=subprocess.PIPE)
    finally:
        for t in tmps:
            os.unlink(t)
    err = p.stderr.decode("utf-8", "replace")
    spatne = []
    for line in err.splitlines(True):
        if line.startswith(ZNACKA):
            parts = line.split(None, 2)
            if len(parts) >= 2 and parts[1] in ("429", "503"):
                spatne.append((parts[1], parts[2].strip() if len(parts) > 2 else ""))
        elif line.strip() or not urls:
            sys.stderr.write(line)
    sys.stderr.flush()
    for kod, url in spatne:
        klic = web(urllib.parse.urlsplit(url).hostname) or (list(po_webech)[0] if urls and po_webech else None)
        if klic:
            zablokuj(klic, kod, url)
    if spatne:
        konec(f"omezovač: web vrátil HTTP {spatne[0][0]} – zablokován na 30 minut, nástroj ukončen "
              "a požadavek se neopakuje.")
    return p.returncode


# ---------- spouštění nástrojů ----------
def _env_potomka(znacka):
    env = dict(os.environ)
    env["PATH"] = BIN + os.pathsep + env.get("PATH", "")
    env["OMEZ_ZNACKA"] = znacka
    env["OMEZ_PYTHON"] = sys.executable
    return env


def _dozor(cmd):
    """Spustí cmd v nové skupině procesů a počká. Při blokaci (značka) vrátí 75."""
    fd, znacka = tempfile.mkstemp(prefix="omez_", suffix=".blok")
    os.close(fd)
    os.unlink(znacka)
    env = _env_potomka(znacka)
    kw = {}
    if os.name != "nt":
        kw["start_new_session"] = True
    p = subprocess.Popen(cmd, env=env, **kw)   # potomek je vedoucím nové skupiny (pgid = jeho pid)
    try:
        rc = p.wait()
    except KeyboardInterrupt:
        if os.name != "nt":
            os.killpg(p.pid, signal.SIGINT)
        rc = p.wait()
    if os.path.exists(znacka):
        os.unlink(znacka)
        return KOD_BLOK
    return rc


def _python_flags():
    f = ["-I"]
    if sys.flags.utf8_mode:
        f += ["-X", "utf8"]
    return f


def uvnitr(args):
    """Běží v podprocesu (nová skupina procesů): obalí http.client a spustí nástroj / kód."""
    if os.name != "nt":
        os.environ["OMEZ_PGID"] = str(os.getpgrp())
    os.environ["PATH"] = BIN + os.pathsep + os.environ.get("PATH", "").replace(BIN + os.pathsep, "")
    obal_http()
    if args[:1] == ["-c"]:
        sys.argv = ["-c"] + args[2:]
        g = {"__name__": "__main__"}
        exec(compile(args[1], "<omez -c>", "exec"), g)
        return
    import runpy
    tool = os.path.abspath(args[0])
    sys.argv = [args[0]] + args[1:]
    if not getattr(sys.flags, "safe_path", False):
        sys.path[0] = os.path.dirname(tool)
    runpy.run_path(tool, run_name="__main__")


def skript(args):
    """Shellový skript: curl v něm jde přes bin/curl; skripty s prohlížečem dostanou předem slot „stránka“."""
    path = args[0]
    name = os.path.basename(path)
    klic = PROHLIZEC.get(name)
    if klic:
        try:
            slot = vyhrad(klic, "stranka")
            d = slot - time.time()
            if d > 0:
                time.sleep(d)
        except Zablokovano as e:
            sys.stderr.write(str(e) + "\n")
            return KOD_BLOK
    shell = "bash"
    try:
        first = open(path, encoding="utf-8", errors="replace").readline()
        if first.startswith("#!"):
            shell = os.path.basename(first[2:].split()[-1] if "env" in first else first[2:].split()[0])
    except OSError:
        pass
    return _dozor([shutil.which(shell) or shell, path] + args[1:])


def stav():
    if not os.path.isdir(STAV):
        print("Žádný web zatím nebyl použit.")
        return 0
    now = time.time()
    for f in sorted(os.listdir(STAV)):
        if f.endswith(".json"):
            klic, st = f[:-5], _cti(f[:-5])
            b = st.get("blok_do", 0)
            co = (f"ZABLOKOVÁN do {time.strftime('%H:%M', time.localtime(b))} ({st.get('duvod', '')})"
                  if b > now else "v pořádku")
            fronta = ", ".join(f"{k} +{max(0, st.get(k, 0) - now):.0f} s" for k in INTERVAL if st.get(k, 0) > now)
            print(f"{klic}: {co}" + (f"; fronta: {fronta}" if fronta else ""))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "--uvnitr":
        uvnitr(argv[1:])
        return 0
    if cmd == "stav":
        return stav()
    if cmd == "curl":
        return curl(argv[1:])
    if cmd in ("python", "python3", "py"):
        rest = argv[1:]
        while rest and rest[0] in ("-I", "-X", "utf8", "-u", "-B"):   # přepínače interpretu omezovač nastaví sám
            rest = rest[1:]
        return _dozor([sys.executable] + _python_flags() + [os.path.abspath(__file__), "--uvnitr"] + rest)
    if cmd.endswith(".py"):
        return _dozor([sys.executable] + _python_flags() + [os.path.abspath(__file__), "--uvnitr"] + argv)
    if cmd.endswith(".sh"):
        return skript(argv)
    if cmd == "web" and len(argv) >= 3:            # libovolný příkaz (např. osascript s prohlížečem) pro daný web
        cil = argv[1]
        klic = web(urllib.parse.urlsplit(cil).hostname if "://" in cil else cil)
        if klic:
            try:
                slot = vyhrad(klic, "stranka")
            except Zablokovano as e:
                sys.stderr.write(str(e) + "\n")
                return KOD_BLOK
            if slot > time.time():
                time.sleep(slot - time.time())
        rest = argv[3:] if argv[2] == "--" else argv[2:]
        return _dozor(rest)
    sys.stderr.write(f"omezovač: neznámý příkaz „{cmd}“ (čekám nástroj .py/.sh, curl, python, web nebo stav)\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
