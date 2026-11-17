#!/bin/zsh
# aron_obrazovka.sh <apu knihy> <pořadí snímku> <out.jpg> [x0,y0,x1,y1]
# Snímek z prohlížeče ARON MZA (lánové rejstříky, fond D 1) uloží tak, jak by to udělal člověk: otevře snímek
# v prohlížeči ARON, počká, až ho prohlížeč sám načte a vykreslí, a uloží pohled (jako „Uložit obrázek jako…“).
# Žádné vlastní stahování dlaždic. Volá ho tools/lanove.py snimek (ten připraví pracovni/aron_paths/<apu>.txt).
# Volitelná oblast = zlomky 0–1 POHLEDU (např. pravá polovina 0.5,0,1,1): přiblíží se kolečkem myši jako uživatel.
# ARON nevykresluje zakryté okno → prohlížeč se na chvíli dá dopředu a pak se vrátí předchozí aplikace.
# Šetrnost: jeden snímek najednou ze všech projektů (společný zámek s MZA ~/.cache/rodokmen-mza), pauza RODOKMEN_MZA_PAUZA (20 s).
cd "$(dirname "$0")/.."
[[ $# -ge 3 ]] || { sed -n 2,8p "$0"; exit 1; }
apu=$1; n=$2; out=$3; oblast=${4:-}
source tools/prohlizec.sh
js() { prohlizec_js "mza.cz/aron" "$1" | tr -d '\r'; }

L=$HOME/.cache/rodokmen-mza; mkdir -p $L
for i in {1..600}; do
  mkdir $L/zamek 2>/dev/null && break
  [[ -n $(find $L/zamek -maxdepth 0 -mmin +5 2>/dev/null) ]] && rmdir $L/zamek 2>/dev/null && continue
  sleep 1
done
[[ -d $L/zamek ]] || { echo "ARON: jiný běh stahuje přes 10 minut – zkus to později" >&2; exit 1; }
predtim=$(osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' 2>/dev/null)
trap 'touch $L/posledni; rmdir $L/zamek 2>/dev/null; [[ -n $predtim ]] && osascript -e "tell application \"$predtim\" to activate" >/dev/null 2>&1' EXIT INT TERM
pauza=${RODOKMEN_MZA_PAUZA:-20}; (( pauza < 3 )) && pauza=3
if [[ -f $L/posledni ]]; then
  w=$(( pauza - ($(date +%s) - $(stat -f %m $L/posledni)) )); (( w > 0 )) && sleep $w
fi

img=$(sed -n "${n}p" pracovni/aron_paths/$apu.txt 2>/dev/null)
[[ -n $img ]] || { echo "snímek $n knihy $apu není (spusť python3 -I tools/lanove.py snimek …)" >&2; exit 1; }
url="https://www.mza.cz/aron/apu/$apu/dao/$apu/file/$img"
tady=$(js "location.href")
if [[ $tady == NO-TAB ]]; then prohlizec_otevri "$url"; elif [[ $tady != *$img* ]]; then js "location.href='$url';'ok'" >/dev/null; else js "location.reload();'ok'" >/dev/null; fi
osascript -e "tell application \"$PROHLIZEC\" to activate" >/dev/null 2>&1

cekej() {
  prev=x; same=0; st=?
  for i in {1..120}; do
    sleep 1
    st=$(js "location.href.indexOf('$img')<0||document.readyState!='complete'?'čeká':(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];if(!c||c.width<400)return 'čeká';try{var g=c.getContext('2d').getImageData(0,0,c.width,c.height).data,m=0,k=0;for(var j=0;j<g.length;j+=4004){m+=g[j]+g[j+1]+g[j+2];k++}if(m/k/3<25)return 'čeká';return c.width+'x'+c.height+':'+c.toDataURL('image/jpeg',0.5).length}catch(e){return 'chyba '+e.name}})()")
    [[ $st == chyba* || $st == NO-TAB ]] && { echo "ARON: $st – přestaň a zkus to až později" >&2; exit 1; }
    if [[ $st != čeká && $st == $prev ]]; then (( same++ )); (( same >= 3 )) && break; else same=0; fi
    prev=$st
  done
  (( same >= 3 )) || { echo "ARON: obrázek se v prohlížeči nenačetl (stav $st) – přestaň a zkus to až později" >&2; exit 1; }
}
cekej

# skutečné události myši/klávesnice (CGEvent) – vyžaduje Zpřístupnění pro terminál (Nastavení → Soukromí a zabezpečení)
jxa=$(mktemp -t aron).js
cat > $jxa <<'JXA'
ObjC.import('CoreGraphics');
function run(a){var co=a[0],x=+a[1],y=+a[2],n=+(a[3]||1);var p=$.CGPointMake(x,y);
 if(co=='esc'){[true,false].forEach(function(d){$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateKeyboardEvent(null,53,d))});return 'ok'}
 $.CGEventPost($.kCGHIDEventTap,$.CGEventCreateMouseEvent(null,$.kCGEventMouseMoved,p,0));delay(0.3);
 if(co=='tah'){var dx=+a[3],dy=+a[4];$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateMouseEvent(null,$.kCGEventLeftMouseDown,p,$.kCGMouseButtonLeft));delay(0.1);for(var k=1;k<=20;k++){$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateMouseEvent(null,$.kCGEventLeftMouseDragged,$.CGPointMake(x+dx*k/20,y+dy*k/20),$.kCGMouseButtonLeft));delay(0.03)}delay(0.1);$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateMouseEvent(null,$.kCGEventLeftMouseUp,$.CGPointMake(x+dx,y+dy),$.kCGMouseButtonLeft));return 'ok'}
 if(co=='klik'){[$.kCGEventLeftMouseDown,$.kCGEventLeftMouseUp].forEach(function(t){$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateMouseEvent(null,t,p,$.kCGMouseButtonLeft));delay(0.05)});return 'ok'}
 for(var i=0;i<n;i++){$.CGEventPost($.kCGHIDEventTap,$.CGEventCreateScrollWheelEvent(null,1,1,3));delay(0.25);}return 'ok';}
JXA
udalost() { osascript -e "tell application \"$PROHLIZEC\" to activate" >/dev/null 2>&1; sleep 0.3; osascript -l JavaScript $jxa "$@" >/dev/null || { echo "ARON: událost myši se nepodařilo poslat (povol Zpřístupnění pro terminál)" >&2; exit 1; }; }
trap 'touch $L/posledni; rmdir $L/zamek 2>/dev/null; rm -f $jxa; [[ -n $predtim ]] && osascript -e "tell application \"$predtim\" to activate" >/dev/null 2>&1' EXIT INT TERM
# celá obrazovka (tlačítko v liště prohlížeče) = větší plátno
cela=
if [[ -z $oblast && ${RODOKMEN_ARON_CELA:-1} == 1 ]]; then
  b=$(js "(function(){var e=Array.from(document.querySelectorAll('[title]')).find(x=>x.title=='Celá obrazovka');if(!e)return '';var r=e.getBoundingClientRect();return Math.round(screenX+r.left+r.width/2)+' '+Math.round(screenY+(outerHeight-innerHeight)+r.top+r.height/2)})()")
  if [[ -n $b ]]; then udalost klik ${=b}; cela=1; sleep 2; cekej; fi
fi

if [[ -n $oblast ]]; then
  # skutečné otočení kolečkem myši (CGEvent) nad bodem, kolem kterého se přibližuje – vyžaduje Zpřístupnění pro terminál
  IFS=, read x0 y0 x1 y1 <<< "$oblast"
  # přiblížit kolečkem nad středem pohledu (u okrajů leží ovládací prvky), pak posunout tažením myši na střed oblasti
  bod=$(js "(function(){var c=document.querySelector('.openseadragon-canvas'),r=c.getBoundingClientRect();var f=1/Math.max($x1-$x0,$y1-$y0),K=${RODOKMEN_ARON_KROK:-1.25},N=Math.max(1,Math.round(Math.log(f)/Math.log(K))),F=Math.pow(K,N);var x=Math.round(screenX+r.left+r.width/2),y=Math.round(screenY+(outerHeight-innerHeight)+r.top+r.height/2);var dx=Math.round((0.5-($x0+$x1)/2)*r.width*F),dy=Math.round((0.5-($y0+$y1)/2)*r.height*F);return x+' '+y+' '+N+' '+dx+' '+dy})()")
  set -- ${=bod}
  udalost kolecko $1 $2 $3
  sleep 1; cekej
  (( $4 != 0 || $5 != 0 )) && { udalost tah $1 $2 $4 $5; sleep 1; cekej; }
  sleep 1; cekej
fi

js "(function(){var c=Array.from(document.querySelectorAll('.openseadragon-canvas canvas')).sort((a,b)=>b.width*b.height-a.width*a.height)[0];window.__rk={url:c.toDataURL('image/jpeg',0.92),st:c.width+'x'+c.height};return 'ok'})()" >/dev/null
len=$(js "window.__rk.url.length"); start=$(js "window.__rk.url.indexOf(',')+1"); tmp=$(mktemp); : > $tmp
for (( o=start; o<len; o+=400000 )); do js "window.__rk.url.substr($o,400000)" | tr -d '\n' >> $tmp; done
size=$(js "window.__rk.st"); js "window.__rk=null;'ok'" >/dev/null
mkdir -p "$(dirname "$out")"; base64 -D -i $tmp -o "$out"; rm -f $tmp
[[ -n $cela ]] && udalost esc 0 0
echo "$out: $size px (pohled prohlížeče ARON)"
