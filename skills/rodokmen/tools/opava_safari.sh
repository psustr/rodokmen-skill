#!/bin/zsh
# ZA Opava (digi.archives.cz) bez Chrome/Playwright – přes uživatelovo Safari a AppleScript (macOS).
# Jednou předem: Safari → Nastavení → Pokročilé „Zobrazovat funkce pro vývojáře“, Vývojář → „Povolit JavaScript z událostí Apple“.
# Snímky pak stahuje tools/soal_zoomify.py z images.archives.cz (bez prohlížeče, bez limitu).
#
#   opava_safari.sh hledat "Obec" [od] [do]          → seznam matrik obce (název | roky | signatura | snímků)
#   opava_safari.sh otevri "Obec" "Př VIII 45" [od] [do]
#                                                    → nové hledání, otevře knihu, uloží ID snímků do pracovni/opava/<kniha>.scans
#   opava_safari.sh adresa <kniha> <snímek>          → adresa obrázku (kniha musí být v kartě otevřená; ukládá do <kniha>.urls)
#   opava_safari.sh adresy <kniha> <od> <do>         → pomalu zjistí adresy rozsahu snímků (pro pomocníka bez prohlížeče)
#   opava_safari.sh js '<javascript>'                → spustí JS v kartě s digi.archives.cz
# <kniha> = signatura bez mezer (Př VIII 45 → PrVIII45). Relace badatelny vyprší asi po hodině nečinnosti → znovu `otevri`.
# Po ~10 rychlých dotazech vrací ochrana (Radware) místo stránky ověření – skript kartu obnoví a zkusí znovu.
cd "$(dirname "$0")/.."; D=pracovni/opava; mkdir -p $D
js() { osascript - "$1" <<'AS' | tr -d '\r'
on run argv
tell application "Safari"
  repeat with w in windows
    repeat with t in tabs of w
      if URL of t contains "digi.archives.cz" then return (do JavaScript (item 1 of argv) in t)
    end repeat
  end repeat
  return "NO-TAB"
end tell
end run
AS
}
num_ok() { [[ -n $1 && $1 != 0 && $1 != 0.0 && $1 != NO-TAB ]]; }
slug() { echo "$1" | tr -d ' ' | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null | tr -cd 'A-Za-z0-9'; }
search() {   # $1 obec, $2 od, $3 do
  if [[ $(js 1) == NO-TAB ]]; then
    osascript -e 'tell application "Safari" to tell front window to set current tab to (make new tab with properties {URL:"https://digi.archives.cz/da/"})' >/dev/null
  else js 'location.href="https://digi.archives.cz/da/";"ok"' >/dev/null; fi
  for i in {1..20}; do sleep 2; [[ $(js '!!document.getElementById("patternTxt")') == true ]] && break; done
  js "var l=document.querySelector('label[data-tooltip^=Matriky]'); var c=document.getElementById(l.getAttribute('for')); if(!c.checked)c.click(); document.getElementById('patternTxt').value='$1'; document.getElementById('timeRangeFrom').value='$2'; document.getElementById('timeRangeTo').value='$3'; document.querySelector('button.inputSubmit').click(); 'ok'" >/dev/null
  for i in {1..20}; do sleep 2; [[ $(js 'location.href') == *vysledekList* ]] && num_ok "$(js 'document.querySelectorAll("li.minicard").length')" && break; done
}
LIST='Array.from(document.querySelectorAll("li.minicard")).map(li=>{var a=li.querySelector("a.link");var s=li.querySelector("a.scan");return a.textContent.trim()+" | "+li.querySelector(".vznik").textContent+" | "+(li.querySelector(".textDotted").textContent.match(/sign\. [^•]+/)||[""])[0].trim()+" | "+(s?s.textContent.trim():"0")+" sn."}).join("\n")'
page2() { js 'location.href="https://digi.archives.cz/da/vysledekList?page=2&actualRow=&actualUuid=";"ok"' >/dev/null; sleep 6; }
url_of() {   # $1 kniha, $2 snímek
  local f=$D/$1; local c; c=$(grep "^$2 " $f.urls 2>/dev/null | cut -d' ' -f2); [[ -n $c ]] && { echo $c; return; }
  local v id u ent; v=$(sed -n "$2p" $f.scans); id=${v#*%20}; ent=$(cat $f.entity)
  for t in 1 2 3; do
    u=$(js "var x=new XMLHttpRequest();x.open('GET','/da/showZoomify/$ent/$id',false);x.send();(x.responseText.match(/https:\/\/images\.archives\.cz[^\"' ]*?\.(jpg|JPG)/)||['ERR'])[0]")
    [[ $u == https* ]] && { echo "$2 $u" >> $f.urls; echo $u; return; }
    js 'location.reload();"ok"' >/dev/null; sleep 20
  done
  echo "ERR – relace vypršela? spusť znovu: opava_safari.sh otevri …" >&2; return 1
}
case $1 in
  js) js "$2" ;;
  hledat) search "$2" "${3:-1780}" "${4:-1910}"; js "$LIST"; page2; js "$LIST" ;;
  otevri)
    k=$(slug "$3"); search "$2" "${4:-1780}" "${5:-1910}"
    for p in 1 2; do
      h=$(js "var sig='$3'; var li=Array.from(document.querySelectorAll('li.minicard')).find(x=>{var t=x.textContent.replace(/\\s+/g,' ')+' '; var i=t.indexOf('sign. '+sig); return i>=0 && !/[0-9]/.test(t[i+6+sig.length]);}); li&&li.querySelector('a.scan')?li.querySelector('a.scan').getAttribute('href'):''")
      [[ -n $h ]] && break; page2
    done
    [[ -z $h ]] && { echo "kniha $3 ve výsledcích není"; exit 1; }
    js "location.href='https://digi.archives.cz$h';'ok'" >/dev/null
    for i in {1..30}; do sleep 2; n=$(js 'document.querySelectorAll("select.getScanSelect option").length'); num_ok "$n" && break; done
    js 'document.querySelector("[entityuuid]").getAttribute("entityuuid")' > $D/$k.entity
    js 'Array.from(document.querySelectorAll("select.getScanSelect option")).map(o=>o.value).join("\n")' | tr '\r' '\n' > $D/$k.scans
    echo "otevřeno: $3 → $D/$k.scans ($(wc -l < $D/$k.scans | tr -d ' ') snímků)" ;;
  adresa) url_of "$2" "$3" ;;
  adresy) for n in {$3..$4}; do url_of "$2" $n >/dev/null && echo "$n ok" || exit 1; sleep 4; done ;;
  *) sed -n 2,14p "$0" ;;
esac
