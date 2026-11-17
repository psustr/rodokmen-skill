#!/bin/zsh
# mza_obrazovka.sh <id knihy> <pořadí snímku> <out.jpg>
# Snímek matriky MZA uloží tak, jak by to udělal člověk: otevře snímek v prohlížeči MZA (stránka knihy s ?image=…),
# počká, až prohlížeč obrázek sám načte a vykreslí, a uloží to, co je na plátně – stejně jako „Uložit obrázek jako…“
# (pravé tlačítko na obrázku). Žádné vlastní stahování dlaždic: archiv dostane jen požadavky, které by poslal
# i prohlížeč při ručním listování. Rozlišení = velikost okna prohlížeče (na Retině ~2900 px) – na čtení stačí;
# větší okno = větší obrázek.
# Šetrnost: jeden snímek najednou ze všech projektů (zámek ~/.cache/rodokmen-mza), pauza RODOKMEN_MZA_PAUZA (výchozí 20 s).
# Předpoklad: tools/mza_safari.sh <id> (jednou – uloží seznam snímků knihy do pracovni/mza_paths/<id>.txt).
cd "$(dirname "$0")/.."
[[ $# -ge 3 ]] || { sed -n 2,9p "$0"; exit 1; }
id=$1; n=$2; out=$3
source tools/prohlizec.sh
js() { prohlizec_js "mza.cz/actapublica" "$1" | tr -d '\r'; }

L=$HOME/.cache/rodokmen-mza; mkdir -p $L
for i in {1..600}; do
  mkdir $L/zamek 2>/dev/null && break
  [[ -n $(find $L/zamek -maxdepth 0 -mmin +5 2>/dev/null) ]] && rmdir $L/zamek 2>/dev/null && continue
  sleep 1
done
[[ -d $L/zamek ]] || { echo "MZA: jiný běh stahuje přes 10 minut – zkus to později" >&2; exit 1; }
trap 'touch $L/posledni; rmdir $L/zamek 2>/dev/null' EXIT INT TERM
pauza=${RODOKMEN_MZA_PAUZA:-20}; (( pauza < 3 )) && pauza=3
if [[ -f $L/posledni ]]; then
  w=$(( pauza - ($(date +%s) - $(stat -f %m $L/posledni)) )); (( w > 0 )) && sleep $w
fi

[[ -s pracovni/mza_paths/$id.txt ]] || { rmdir $L/zamek 2>/dev/null; zsh tools/mza_safari.sh $id >&2 || exit 1; mkdir $L/zamek 2>/dev/null; }
img=$(sed -n "${n}p" pracovni/mza_paths/$id.txt | grep -o '[^/]*\.jp2' | head -1)
[[ -n $img ]] || { echo "snímek $n v knize $id není" >&2; exit 1; }
url="https://www.mza.cz/actapublica/matrika/detail/$id?image=$img"

# otevři snímek v kartě MZA (jako klik v prohlížeči)
if [[ $(js "location.href") == NO-TAB ]]; then prohlizec_otevri "$url"; else js "location.href='$url';'ok'" >/dev/null; fi

# počkej, až je stránka načtená a plátno prohlížeče se přestane měnit (obrázek dokreslen)
prev=x; same=0; st=?
for i in {1..90}; do
  sleep 2
  st=$(js "location.href.indexOf('$img')<0||document.readyState!='complete'?'čeká':(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];if(!c||c.width<400)return 'čeká';try{var d=c.toDataURL('image/jpeg',0.5);return c.width+'x'+c.height+':'+d.length}catch(e){return 'chyba '+e.name}})()")
  [[ $st == chyba* || $st == NO-TAB ]] && { echo "MZA: $st – přestaň a zkus to až později" >&2; exit 1; }
  if [[ $st != čeká && $st == $prev ]]; then (( same++ )); (( same >= 3 )) && break; else same=0; fi
  prev=$st
done
(( same >= 3 )) || { echo "MZA: obrázek se v prohlížeči nenačetl (stav $st) – přestaň a zkus to až později" >&2; exit 1; }

# ulož plátno („Uložit obrázek jako…“)
js "(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];window.__rk={url:c.toDataURL('image/jpeg',0.92),st:c.width+'x'+c.height};return 'ok'})()" >/dev/null
len=$(js "window.__rk.url.length"); start=$(js "window.__rk.url.indexOf(',')+1"); tmp=$(mktemp); : > $tmp
for (( o=start; o<len; o+=400000 )); do js "window.__rk.url.substr($o,400000)" | tr -d '\n' >> $tmp; done
size=$(js "window.__rk.st"); js "window.__rk=null;'ok'" >/dev/null
mkdir -p "$(dirname "$out")"; base64 -D -i $tmp -o "$out"; rm -f $tmp
echo "$out: $size px (pohled prohlížeče)"
