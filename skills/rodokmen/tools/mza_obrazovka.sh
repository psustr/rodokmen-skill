#!/bin/zsh
# mza_obrazovka.sh <id knihy> <pořadí snímku> <out.jpg> [x0,y0,x1,y1]
# Volitelná oblast (zlomky 0–1 šířky a výšky snímku): prohlížeč ji přiblíží (jako zoom myší) a uloží jen ji – vyšší rozlišení.
# Snímek matriky MZA uloží tak, jak by to udělal člověk: otevře snímek v prohlížeči MZA (stránka knihy s ?image=…),
# počká, až prohlížeč obrázek sám načte a vykreslí, a uloží to, co je na plátně – stejně jako „Uložit obrázek jako…“
# (pravé tlačítko na obrázku). Žádné vlastní stahování dlaždic: archiv dostane jen požadavky, které by poslal
# i prohlížeč při ručním listování. Rozlišení = velikost okna prohlížeče (na Retině ~2900 px) – na čtení stačí;
# větší okno = větší obrázek.
# Zakryté okno prohlížeč nepřekresluje – skript proto kartu na chvíli vyvolá dopředu a pak vrátí předchozí aplikaci.
# Šetrnost: jeden snímek najednou ze všech projektů (zámek ~/.cache/rodokmen-mza), pauza RODOKMEN_MZA_PAUZA (výchozí 20 s).
# Předpoklad: tools/mza_safari.sh <id> (jednou – uloží seznam snímků knihy do pracovni/mza_paths/<id>.txt).
cd "$(dirname "$0")/.."
[[ $# -ge 3 ]] || { sed -n 2,9p "$0"; exit 1; }
id=$1; n=$2; out=$3; oblast=${4:-}
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
tady=$(js "location.href")
if [[ $tady == NO-TAB ]]; then prohlizec_otevri "$url"; elif [[ $tady != *$img* ]]; then js "location.href='$url';'ok'" >/dev/null; fi

# počkej, až je stránka načtená a plátno prohlížeče se přestane měnit (obrázek dokreslen)
cekej() {
prev=x; same=0; st=?; skryto=0
for i in {1..90}; do
  sleep 2
  st=$(js "location.href.indexOf('$img')<0||document.readyState!='complete'?'čeká':document.hidden?'skryto':(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];if(!c||c.width<400)return 'čeká';try{var g=c.getContext('2d').getImageData(0,0,c.width,c.height).data,m=0,k=0;for(var j=0;j<g.length;j+=4004){m+=g[j]+g[j+1]+g[j+2];k++}if(m/k/3<25)return 'čeká';var d=c.toDataURL('image/jpeg',0.5);return c.width+'x'+c.height+':'+d.length}catch(e){return 'chyba '+e.name}})()")
  if [[ $st == skryto ]]; then
    [[ -z $pred ]] && pred=$(prohlizec_popredi "mza.cz/actapublica")
    (( skryto++ >= 5 )) && { echo "MZA: okno $PROHLIZEC je skryté i po vyvolání (jiná plocha, okno na celou obrazovku?) – dej ho na viditelné místo" >&2; exit 1; }
    continue
  fi
  [[ $st == chyba* || $st == NO-TAB ]] && { echo "MZA: $st – přestaň a zkus to až později" >&2; exit 1; }
  if [[ $st != čeká && $st == $prev ]]; then (( same++ )); (( same >= 3 )) && break; else same=0; fi
  prev=$st
done
(( same >= 3 )) || { echo "MZA: obrázek se v prohlížeči nenačetl (stav $st) – přestaň a zkus to až později" >&2; exit 1; }
}
pred=
trap 'prohlizec_vrat "$pred"; touch $L/posledni; rmdir $L/zamek 2>/dev/null' EXIT INT TERM
cekej
if [[ -n $oblast ]]; then
  IFS=, read x0 y0 x1 y1 <<< "$oblast"
  # přiblížit a ověřit, že pohled opravdu ukazuje oblast (prohlížeč ho po změně velikosti okna může vrátit)
  ok=
  for pokus in 1 2 3; do
    js "(function(){var h=viewer.world.getItemAt(0).getBounds().height;viewer.viewport.fitBounds(new OpenSeadragon.Rect($x0,$y0*h,$x1-$x0,($y1-$y0)*h),true);return 'ok'})()" >/dev/null
    sleep 1; cekej
    ok=$(js "(function(){var h=viewer.world.getItemAt(0).getBounds().height,b=viewer.viewport.getBounds(true),cx=($x0+$x1)/2,cy=($y0+$y1)/2*h;return Math.abs(b.x+b.width/2-cx)<0.02&&Math.abs(b.y+b.height/2-cy)<0.02&&Math.min(b.width/($x1-$x0),b.height/(($y1-$y0)*h))<1.15?'ano':'ne'})()")
    [[ $ok == ano ]] && break
  done
  [[ $ok == ano ]] || { echo "MZA: přiblížení se nepodařilo – zkus to znovu" >&2; exit 1; }
fi

# ulož plátno („Uložit obrázek jako…“)
js "(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];window.__rk={url:c.toDataURL('image/jpeg',0.92),st:c.width+'x'+c.height};return 'ok'})()" >/dev/null
len=$(js "window.__rk.url.length"); start=$(js "window.__rk.url.indexOf(',')+1"); tmp=$(mktemp); : > $tmp
for (( o=start; o<len; o+=400000 )); do js "window.__rk.url.substr($o,400000)" | tr -d '\n' >> $tmp; done
size=$(js "window.__rk.st"); js "window.__rk=null;'ok'" >/dev/null
mkdir -p "$(dirname "$out")"; base64 -D -i $tmp -o "$out"; rm -f $tmp
echo "$out: $size px (pohled prohlížeče)"
