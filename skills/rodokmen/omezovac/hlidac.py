#!/usr/bin/env python3
"""hlidac.py – hook PreToolUse pro Claude Code: zamítne síťové příkazy, které nejdou přes omezovač (omez.py).

Hlídá jen v projektu rodokmenu (složka s .skill_verze nebo data/STAV.md + data/osoby.py) nebo když příkaz míří
na web archivu či na síťový nástroj skillu – jinde (jiné projekty uživatele) nic nezakazuje.
  * Bash / Monitor: curl, wget a spol., síťové nástroje z tools/, Python s urllib/http.client/requests/socket,
    osascript s prohlížečem → musí jít přes `python3 -I SKILL_DIR/omezovac/omez.py …`, jinak zamítnuto.
  * WebFetch: zablokovaný web zamítne; jinak si vyhradí slot „stránka“ (1 za 2 s) a počká na něj.
Vstup: JSON od Claude Code na stdin. Výstup: při zamítnutí JSON s permissionDecision "deny".
Když hlídač sám selže, příkaz nezastaví (vypíše chybu) – pravidla v SKILL.md platí i tak.
Zapojení: plugin (hooks/hooks.json v kořeni repozitáře) nebo ručně v .claude/settings.json projektu:
  {"hooks": {"PreToolUse": [{"matcher": "Bash|WebFetch|Monitor",
     "hooks": [{"type": "command", "command": "python3 -I /cesta/ke/skillu/omezovac/hlidac.py", "timeout": 120}]}]}}
"""
import json
import os
import re
import shlex
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import omez  # noqa: E402

SIT = {"curl", "curl.exe", "wget", "wget2", "aria2c", "http", "https", "httpie", "xh", "nc", "ncat", "netcat",
       "telnet", "ftp", "sftp", "lynx", "w3m", "links", "elinks", "lftp", "rsync", "scp", "yt-dlp", "gallery-dl"}
NASTROJE = {"ahmp_scan.py", "ahmp_search.sh", "anno_snap.py", "anno.py", "aron_img.py", "aron_obrazovka.sh",
            "aron_search.py", "ebadatelna.py", "ged_fotky.py", "kramerius.py", "lanove.py", "matricula_batch.sh",
            "matricula_dl.sh", "mista.py", "mza.py", "mza_obrazovka.sh", "mza_safari.sh", "mza_snimek.sh",
            "opava_safari.sh", "policie_prihlasky.py", "portafontium.py", "soal_zoomify.py", "trebon.py", "prohlizec.sh"}
PY_SIT = re.compile(r"\b(urllib|urlopen|http\.client|httplib|requests|httpx|aiohttp|urllib3|socket|ftplib|pycurl)\b")
NODE_SIT = re.compile(r"\bfetch\s*\(|require\(['\"](https?|node:https?)['\"]\)|XMLHttpRequest")
PROHL = re.compile(r"(Safari|Google Chrome|Chromium|Firefox|Microsoft Edge|Brave)", re.I)
ARCHIVY = re.compile(r"(mza\.cz|archives\.cz|vychodoceskearchivy\.cz|portafontium\.eu|soapraha\.cz|ahmp\.cz|"
                     r"ceskearchivy\.cz|soalitomerice\.cz|matricula-online\.eu|nacr\.cz|onb\.ac\.at|nkp\.cz|"
                     r"familysearch\.org|geni\.com|myheritage\.|openstreetmap\.org|kramerius|digi\.|aron\.)", re.I)
OMEZ = "omez.py"


def v_projektu(cwd):
    d = os.path.abspath(cwd or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, ".skill_verze")) or (
                os.path.exists(os.path.join(d, "data", "STAV.md")) and os.path.exists(os.path.join(d, "data", "osoby.py"))):
            return True
        nd = os.path.dirname(d)
        if nd == d:
            return False
        d = nd


def useky(cmd):
    """Rozdělí příkaz na jednoduché příkazy (podle ; && || | & a nových řádků) – seznamy slov."""
    out = []
    for radek in cmd.split("\n"):
        try:
            lex = shlex.shlex(radek, posix=True, punctuation_chars=";&|")
            lex.whitespace_split = True
            lex.commenters = ""
            cur = []
            for t in lex:
                if t and set(t) <= set(";&|"):
                    out.append(cur)
                    cur = []
                else:
                    cur.append(t)
            out.append(cur)
        except ValueError:                       # neuzavřené uvozovky (heredoc, víceřádkový řetězec) – hrubě
            for kus in re.split(r"&&|\|\||[;|&]", radek):
                out.append(kus.split())
    return [u for u in out if u]


def posoud(cmd):
    """Vrátí důvod zamítnutí, nebo None."""
    cely_py_sit = bool(PY_SIT.search(cmd))
    for slova in useky(cmd):
        jmena = [os.path.basename(w) for w in slova]
        i_omez = next((i for i, j in enumerate(jmena) if j == OMEZ), None)

        def pres_omez(i):
            return i_omez is not None and i_omez < i

        for i, (w, j) in enumerate(zip(slova, jmena)):
            if j in SIT and not pres_omez(i):
                cil = " ".join(slova[i + 1:])
                if re.search(r"https?://(localhost|127\.0\.0\.1|\[::1\])[:/]", cil) and not re.search(
                        r"https?://(?!localhost|127\.0\.0\.1|\[::1\])", cil):
                    continue                     # jen místní náhled webu
                return (f"`{j}` mimo omezovač. Spusť: python3 -I {omez.HERE}/omez.py curl … "
                        "(omezovač hlídá rychlost a blokace webů archivů).")
            if j in NASTROJE and not pres_omez(i):
                return (f"Síťový nástroj {j} mimo omezovač. Spusť: python3 -I {omez.HERE}/omez.py tools/{j} …")
            if re.fullmatch(r"python[0-9.]*(\.exe)?|py", j) and not pres_omez(i):
                rest = slova[i + 1:]
                inline = "-c" in rest or "-" in rest or not any(x.endswith(".py") for x in rest)
                if inline and cely_py_sit:
                    return ("Python se síťovým kódem (urllib/http.client/requests/socket) mimo omezovač. Spusť: "
                            f"python3 -I {omez.HERE}/omez.py python -c \"…\" (nebo kód ulož do souboru a spusť "
                            f"python3 -I {omez.HERE}/omez.py soubor.py).")
            if j in ("node", "deno", "bun") and NODE_SIT.search(cmd) and not pres_omez(i):
                return "Síťový kód v JavaScriptu mimo omezovač – použij omez.py curl nebo omez.py python."
            if j == "osascript" and PROHL.search(cmd) and re.search(r"URL|do JavaScript|execute", cmd) \
                    and not pres_omez(i):
                return (f"Ovládání prohlížeče mimo omezovač. Spusť: python3 -I {omez.HERE}/omez.py web <doména> -- "
                        "osascript … (nebo hotový skript z tools/ přes omez.py).")
    return None


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    vstup = data.get("tool_input") or {}
    projekt = v_projektu(data.get("cwd"))
    duvod = None
    if tool == "WebFetch":
        url = vstup.get("url", "")
        klic = omez.web(urllib.parse.urlsplit(url).hostname)
        if klic and (projekt or ARCHIVY.search(url)):
            try:
                slot = omez.vyhrad(klic, "stranka")
                if slot - time.time() > 100:
                    duvod = f"Fronta požadavků na {klic} je dlouhá – zkus to za pár minut."
                elif slot > time.time():
                    time.sleep(slot - time.time())
            except omez.Zablokovano as e:
                duvod = str(e)
    else:
        cmd = vstup.get("command")
        if isinstance(cmd, str) and (projekt or ARCHIVY.search(cmd) or any(n in cmd for n in NASTROJE)):
            duvod = posoud(cmd)
    if duvod:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": "rodokmen – omezovač: " + duvod}},
                         ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:                       # hlídač nesmí rozbít práci; pravidla platí i bez něj
        sys.stderr.write(f"hlidac.py: {e}\n")
    sys.exit(0)
