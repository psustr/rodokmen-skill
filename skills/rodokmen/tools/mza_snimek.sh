#!/bin/zsh
# mza_snimek.sh <id knihy> <pořadí snímku> <out.jpg> [-1]
# Snímek matriky MZA (Acta Publica) uloží přímo uživatelův prohlížeč – stejně, jako by si ho uživatel prohlédl a uložil.
# Stránka knihy otevřená v prohlížeči (po ověření „nejste robot“) načte dlaždice svého snímku ze serveru MZA, složí je
# na plátně (canvas) a obrázek předá skriptu. Žádné curl, žádné cizí hlavičky – MZA od 11/2026 požadavky mimo prohlížeč
# odmítá. -1 = poloviční rozlišení (na orientaci), bez něj plné (na čtení a výřezy).
# Šetrnost: jeden snímek najednou ze všech projektů na počítači (zámek ~/.cache/rodokmen-mza), pauza RODOKMEN_MZA_PAUZA
# (výchozí 20 s) mezi snímky, dlaždice jedna po druhé. Při chybě skončí – nezkoušej hned znovu.
# Předpoklad: tools/mza_safari.sh (otevře knihu a uloží adresy snímků do pracovni/mza_paths/<id>.txt).
cd "$(dirname "$0")/.."
[[ $# -ge 3 ]] || { sed -n 2,9p "$0"; exit 1; }
id=$1; n=$2; out=$3; half=0; [[ $4 == -1 ]] && half=1
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

# kniha musí být v kartě otevřená (podepsané adresy platí jen pro ni)
if [[ $(js "location.href.indexOf('detail/$id')>0") != true || ! -s pracovni/mza_paths/$id.txt ]]; then
  rmdir $L/zamek 2>/dev/null; zsh tools/mza_safari.sh $id >&2 || exit 1; mkdir $L/zamek 2>/dev/null
fi
p=$(sed -n "${n}p" pracovni/mza_paths/$id.txt)
[[ -n $p ]] || { echo "snímek $n v knize $id není" >&2; exit 1; }

js "(function(){var R=window.__rk={st:'běží',url:''};var base='$p';
 var x=new XMLHttpRequest();x.open('GET',base+'.dzi',false);x.send();
 if(x.status!=200){R.st='chyba dzi '+x.status;return 'start';}
 var w=+x.responseText.match(/Width=\"(\\d+)/)[1],h=+x.responseText.match(/Height=\"(\\d+)/)[1],ts=+x.responseText.match(/TileSize=\"(\\d+)/)[1];
 var m=Math.max(w,h),lev=Math.ceil(Math.log2(m));if($half){lev--;w=Math.ceil(w/2);h=Math.ceil(h/2);}
 var cols=Math.ceil(w/ts),rows=Math.ceil(h/ts),c=document.createElement('canvas');c.width=w;c.height=h;var g=c.getContext('2d');
 var list=[];for(var y=0;y<rows;y++)for(var xx=0;xx<cols;xx++)list.push([xx,y]);
 function next(i){if(i>=list.length){R.url=c.toDataURL('image/jpeg',0.92);R.st='hotovo '+w+'x'+h;return;}
  var im=new Image();im.onload=function(){g.drawImage(im,list[i][0]*ts,list[i][1]*ts);setTimeout(function(){next(i+1)},60);};
  im.onerror=function(){R.st='chyba dlaždice '+i;};im.src=base+'_files/'+lev+'/'+list[i][0]+'_'+list[i][1]+'.jpg';}
 next(0);return 'start';})()" >/dev/null

for i in {1..300}; do
  sleep 2; st=$(js "window.__rk?window.__rk.st:'?'")
  [[ $st == hotovo* ]] && break
  [[ $st == chyba* || $st == NO-TAB ]] && { echo "MZA: $st – přestaň a zkus to až později" >&2; exit 1; }
done
[[ $st == hotovo* ]] || { echo "MZA: snímek se nesložil včas" >&2; exit 1; }
len=$(js "window.__rk.url.length"); start=$(js "window.__rk.url.indexOf(',')+1"); tmp=$(mktemp); : > $tmp
for (( o=start; o<len; o+=400000 )); do js "window.__rk.url.substr($o,400000)" | tr -d '\n' >> $tmp; done   # bez „data:image/jpeg;base64,“
js "window.__rk=null;'ok'" >/dev/null
mkdir -p "$(dirname "$out")"; base64 -D -i $tmp -o "$out"; rm -f $tmp
echo "$out: ${st#hotovo } px"
