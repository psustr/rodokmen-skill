#!/bin/zsh
# mza_safari.sh <id knihy> [<id> …] – MZA (od 11/2026) chrání matriky ověřením „nejste robot“ a podepsanými adresami
# obrázků. Otevře knihu v prohlížeči (Safari nebo Google Chrome, viz tools/prohlizec.sh; ověření projde samo), uloží
# podepsané adresy všech snímků do pracovni/mza_paths/<id>.txt; pak `tools/mza.py snimek <id> <n> out.jpg` stahuje normálně přes curl (podpis platí pár hodin).
# Jednou předem: Safari → Nastavení → Pokročilé „Zobrazovat funkce pro vývojáře“, Vývojář → „Povolit JavaScript z událostí Apple“;
# Chrome → Zobrazit → Pro vývojáře → „Povolit JavaScript z událostí Apple“. Jeden prohlížeč na projekt: pracovni/prohlizec.txt.
cd "$(dirname "$0")/.."; mkdir -p pracovni/mza_paths
source tools/prohlizec.sh   # Safari nebo Google Chrome: RODOKMEN_PROHLIZEC / pracovni/prohlizec.txt
js() { prohlizec_js "mza.cz/actapublica" "$1"; }
for id in "$@"; do
  if [[ $(js '1') == NO-TAB ]]; then
    prohlizec_otevri "https://www.mza.cz/actapublica/matrika/detail/$id"
  else
    js "location.href='https://www.mza.cz/actapublica/matrika/detail/$id';'ok'" >/dev/null
  fi
  prev=x
  for i in {1..40}; do sleep 2   # čekej, až se stránka načte celá (počet snímků se dvakrát po sobě nezmění)
    n=$(js 'location.href.indexOf("detail/'$id'")>0 && document.readyState=="complete" ? (document.documentElement.outerHTML.match(/iip-srv/g)||[]).length : 0' | tr -d '\r')
    [[ $n != 0 && $n != 0.0 && $n != NO-TAB && $n == $prev ]] && break
    prev=$n
  done
  js 'Array.from(new Set((document.documentElement.outerHTML.replace(/\\\//g,"/").match(/iip-srv\/iipsrv\.fcgi\/\d+\/[^?"]+\?Deepzoom=[^"]+?\.jp2(?=\.dzi)/g)||[]))).map(x=>"https://www.mza.cz/"+x).join("\n")' | tr '\r' '\n' | grep . > pracovni/mza_paths/$id.txt
  echo "$id: $(wc -l < pracovni/mza_paths/$id.txt | tr -d ' ') snímků"
done
