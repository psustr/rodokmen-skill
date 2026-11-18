#!/bin/zsh
# aron_obrazovka.sh <apu knihy> <pořadí snímku> <out.jpg> [x0,y0,x1,y1]
# Snímek z ARONu MZA (lánové rejstříky, fond D 1) uloží uživatelův prohlížeč, a to i ve skryté kartě a při zamčené
# obrazovce: v kartě ARONu (mza.cz/aron) načte stejnou knihovnu prohlížeče obrázků, jakou používá MZA (OpenSeadragon
# z mza.cz/actapublica/assets), otevře v ní snímek v dočasném panelu, počká na vykreslení a uloží plátno (jako
# „Uložit obrázek jako“). Žádné dlaždice skriptem, žádné cizí hlavičky – požadavky posílá stránka ARONu.
# Vlastní prohlížeč ARONu ve skryté kartě nevykresluje a nedá se ovládat, proto vlastní panel. Od 18. 11. 2026 MZA
# odmítá (403) snímky ARONu načtené ze stránek Acta Publica – proto karta ARONu, ne karta matrik.
# Oblast (zlomky 0–1 snímku): prohlížeč ji přiblíží – vyšší rozlišení. Velikost panelu RODOKMEN_ARON_PANEL (CSS px,
# výchozí 1600x1000 → plátno ~3200×2000 na Retině).
# Šetrnost: jeden snímek najednou ze všech projektů (zámek ~/.cache/rodokmen-mza), pauza RODOKMEN_MZA_PAUZA (20 s).
# Volá ho tools/lanove.py snimek (ten připraví pracovni/aron_paths/<apu>.txt s adresami snímků).
cd "$(dirname "$0")/.."
[[ $# -ge 3 ]] || { sed -n 2,11p "$0"; exit 1; }
apu=$1; n=$2; out=$3; oblast=${4:-}
source tools/prohlizec.sh
js() { prohlizec_js "mza.cz/aron" "$1" | tr -d '\r'; }
# mw: kód ve světě stránky (Chrome spouští JavaScript z AppleScriptu v odděleném světě – knihovnu stránky nevidí);
# výsledek se vrací přes atribut data-rk. Kód = tělo funkce s return.
mw() {
  local c=$(printf %s "document.documentElement.setAttribute('data-rk',String((function(){try{$1}catch(e){return 'chyba '+e.name}})()))" | base64 | tr -d '\n')
  js "(function(){var s=document.createElement('script');s.textContent=decodeURIComponent(escape(atob('$c')));document.documentElement.appendChild(s);s.remove();return document.documentElement.getAttribute('data-rk')})()"
}

L=$HOME/.cache/rodokmen-mza; mkdir -p $L
for i in {1..600}; do
  mkdir $L/zamek 2>/dev/null && break
  [[ -n $(find $L/zamek -maxdepth 0 -mmin +5 2>/dev/null) ]] && rmdir $L/zamek 2>/dev/null && continue
  sleep 1
done
[[ -d $L/zamek ]] || { echo "ARON: jiný běh stahuje přes 10 minut – zkus to později" >&2; exit 1; }
trap 'mw "try{window.__aronV&&window.__aronV.destroy()}catch(e){}var d=document.getElementById(\"rodokmen-aron\");d&&d.remove();window.__aronV=null;return \"ok\"" >/dev/null 2>&1; js "window.__rk=null;1" >/dev/null 2>&1; touch $L/posledni; rmdir $L/zamek 2>/dev/null' EXIT INT TERM
pauza=${RODOKMEN_MZA_PAUZA:-20}; (( pauza < 3 )) && pauza=3
if [[ -f $L/posledni ]]; then
  w=$(( pauza - ($(date +%s) - $(stat -f %m $L/posledni)) )); (( w > 0 )) && sleep $w
fi

dzi=$(sed -n "${n}p" pracovni/aron_paths/$apu.txt 2>/dev/null)
[[ $dzi == https://www.mza.cz/* ]] || { echo "snímek $n knihy $apu není (spusť python3 -I tools/lanove.py snimek …)" >&2; exit 1; }

# karta ARONu (když žádná není, otevře se stránka knihy v ARONu – jako ruční návštěva) a v ní knihovna prohlížeče MZA
OSDJS=https://www.mza.cz/actapublica/assets/openseadragon/openseadragon.min.js
if [[ $(js "location.href") == NO-TAB ]]; then
  prohlizec_otevri "https://www.mza.cz/aron/apu/$apu"
  for i in {1..30}; do sleep 2; [[ $(js "document.readyState") == complete ]] && break; done
fi
osd=; for i in {1..5}; do [[ $(mw "return typeof OpenSeadragon") == function ]] && { osd=1; break; }; sleep 2; done
if [[ -z $osd ]]; then
  mw "if(!document.getElementById('rodokmen-osd')){var s=document.createElement('script');s.id='rodokmen-osd';s.src='$OSDJS';document.head.appendChild(s)}return 'ok'" >/dev/null
  for i in {1..30}; do sleep 2; [[ $(mw "return typeof OpenSeadragon") == function ]] && break; done
  [[ $(mw "return typeof OpenSeadragon") == function ]] || { echo "ARON: knihovna prohlížeče se do karty ARONu nenačetla – zkus to později" >&2; exit 1; }
fi

IFS=x read pw ph <<< "${RODOKMEN_ARON_PANEL:-1600x1000}"
mw "try{window.__aronV&&window.__aronV.destroy()}catch(e){}var d=document.getElementById('rodokmen-aron');d&&d.remove();d=document.createElement('div');d.id='rodokmen-aron';d.style.cssText='position:fixed;left:0;top:0;width:${pw}px;height:${ph}px;flex:none;z-index:2147483647;background:#000';var e=document.createElement('div');e.style.cssText='width:100%;height:100%';d.appendChild(e);document.documentElement.appendChild(d);var G=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t,o){if(t=='2d')o=Object.assign({},o,{willReadFrequently:true});return G.call(this,t,o)};try{window.__aronV=OpenSeadragon({element:e,tileSources:'$dzi',showNavigationControl:false,showNavigator:false,animationTime:0,blendTime:0,immediateRender:false,preserveImageSizeOnResize:true});window.__aronErr='';window.__aronV.addHandler('open-failed',function(e){window.__aronErr='open-failed '+(e.message||'')});window.__aronV.addHandler('tile-load-failed',function(e){if(/HTTP|40[0-9]|50[0-9]/.test(e.message||''))window.__aronErr='tile-load-failed '+(e.message||'')})}finally{HTMLCanvasElement.prototype.getContext=G}return 'ok'" >/dev/null

cekej() {
  prev=x; same=0; st=?
  for i in {1..300}; do
    sleep 1
    st=$(mw "var v=window.__aronV;if(!v)return 'chyba panel';if(window.__aronErr)return 'chyba MZA odmítá snímek ('+window.__aronErr+') – možná blokace';if(document.hidden){try{v.world.update();v.world.draw()}catch(e){}}var t=v.world.getItemAt(0);if(!t||(t.getFullyLoaded&&!t.getFullyLoaded())||v.imageLoader.jobsInProgress>0)return 'čeká';var c=v.drawer.canvas;try{var g=c.getContext('2d').getImageData(0,0,c.width,c.height).data,m=0,k=0;for(var j=0;j<g.length;j+=4004){m+=g[j]+g[j+1]+g[j+2];k++}if(m/k/3<25)return 'čeká';return c.width+'x'+c.height+':'+c.toDataURL('image/jpeg',0.4).length}catch(e){return 'chyba '+e.name}")
    [[ $st == chyba* || $st == NO-TAB ]] && { echo "ARON: $st – přestaň a zkus to až později" >&2; exit 1; }
    if [[ $st != čeká && $st == $prev ]]; then (( same++ )); (( same >= 3 )) && break; else same=0; fi
    prev=$st
  done
  (( same >= 3 )) || { echo "ARON: obrázek se nenačetl (stav $st) – přestaň a zkus to až později" >&2; exit 1; }
}
for i in {1..30}; do sleep 1; [[ $(mw "return window.__aronV&&window.__aronV.world.getItemCount()>0?'ano':'ne'") == ano ]] && break; done
cekej
if [[ -n $oblast ]]; then
  IFS=, read x0 y0 x1 y1 <<< "$oblast"
  mw "var v=window.__aronV,h=v.world.getItemAt(0).getBounds().height;v.viewport.fitBounds(new OpenSeadragon.Rect($x0,$y0*h,$x1-$x0,($y1-$y0)*h),true);v.forceRedraw();return 'ok'" >/dev/null
  sleep 1; cekej
fi

# plátno prohlížeče je v paměti (willReadFrequently), ne na grafické kartě – kreslí se i při vypnutém displeji
# ulož: obraz z plátna přes kopii v paměti (při vypnutém displeji vrací plátno s GPU černý obraz – kontrola jasu přímo
# v ukládaných pixelech, při černém obrazu počkej a zkus znovu)
ulozeno=
for pokus in {1..10}; do
  (( pokus > 1 )) && { mw "var v=window.__aronV;try{v.world.resetItems();v.forceRedraw()}catch(e){}return 'ok'" >/dev/null; cekej; }
  r=$(js "(function(){var c=document.querySelector('#rodokmen-aron canvas'),w=c.width,h=c.height,x=c.getContext('2d').getImageData(0,0,w,h),g=x.data,m=0,k=0;for(var j=0;j<g.length;j+=4004){m+=g[j]+g[j+1]+g[j+2];k++}if(m/k/3<25)return 'černé';var o=document.createElement('canvas');o.width=w;o.height=h;o.getContext('2d',{willReadFrequently:true}).putImageData(x,0,0);var u=o.toDataURL('image/jpeg',0.92),t=new Image();window.__rk={url:u,st:w+'x'+h};return 'ok'})()")
  [[ $r == ok ]] && { ulozeno=1; break; }
  sleep 5
done
[[ -n $ulozeno ]] || { echo "ARON: prohlížeč vrací černý obraz (vypnutý displej?) – přestaň a zkus to, až displej poběží" >&2; exit 1; }
len=$(js "window.__rk.url.length"); start=$(js "window.__rk.url.indexOf(',')+1"); tmp=$(mktemp); : > $tmp
for (( o=start; o<len; o+=400000 )); do js "window.__rk.url.substr($o,400000)" | tr -d '\n' >> $tmp; done
size=$(js "window.__rk.st")
mkdir -p "$(dirname "$out")"; base64 -D -i $tmp -o "$out"; rm -f $tmp
echo "$out: $size px (snímek ARONu v prohlížeči MZA)"
