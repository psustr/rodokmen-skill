#!/bin/zsh
# prohlizec.sh – společná část mza_safari.sh a opava_safari.sh (načítá se příkazem `source`, sám nic nedělá).
# Spouští JavaScript v kartě prohlížeče přes AppleScript (macOS). Prohlížeč:
#   1. proměnná prostředí RODOKMEN_PROHLIZEC, jinak 2. první řádek pracovni/prohlizec.txt, jinak 3. Safari.
#   Hodnoty: „Safari“ nebo „Google Chrome“ (stačí i „chrome“). Firefox JavaScript z AppleScriptu spouštět neumí.
# Každý projekt si označí vlastní kartu (window.name = "rodokmen-<složka projektu>") a hledá přednostně ji;
# cizí označené karty nebere. RODOKMEN_KARTA=<jméno> dá pomocníkovi vlastní kartu ("rodokmen-<složka>-<jméno>").
# Relace a cookies jsou ale v jednom prohlížeči společné – proto má každý projekt používat jiný prohlížeč.
# Jednou předem: Safari → Vývojář → „Povolit JavaScript z událostí Apple“ (nabídku Vývojář zapne Nastavení → Pokročilé);
# Chrome → Zobrazit → Pro vývojáře → „Povolit JavaScript z událostí Apple“ (View → Developer → Allow JavaScript from Apple Events).

PROHLIZEC=${RODOKMEN_PROHLIZEC:-$(head -n 1 pracovni/prohlizec.txt 2>/dev/null | tr -d '\r')}
PROHLIZEC=${${PROHLIZEC##[[:space:]]#}%%[[:space:]]#}
case ${PROHLIZEC:l} in
  ''|safari) PROHLIZEC=Safari ;;
  chrome|'google chrome') PROHLIZEC="Google Chrome" ;;
  *firefox*) echo "Firefox neumí spouštět JavaScript z AppleScriptu – v pracovni/prohlizec.txt nastav Safari nebo Google Chrome." >&2; exit 2 ;;
  *) echo "Neznámý prohlížeč „$PROHLIZEC“ (RODOKMEN_PROHLIZEC / pracovni/prohlizec.txt) – použij Safari nebo Google Chrome." >&2; exit 2 ;;
esac
KARTA="rodokmen-$(basename "$PWD" | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null | tr -cd 'A-Za-z0-9._-')"
[[ -n $RODOKMEN_KARTA ]] && KARTA="$KARTA-$(echo "$RODOKMEN_KARTA" | tr -cd 'A-Za-z0-9._-')"

# prohlizec_js <část adresy> <javascript> → výsledek z karty (vlastní, jinak neoznačené s tou adresou), nebo NO-TAB
prohlizec_js() {
  local err out
  err=$(mktemp -t rodokmen)
  if [[ $PROHLIZEC == Safari ]]; then
    out=$(osascript - "$1" "$KARTA" "window.name=\"$KARTA\";$2" 2>"$err" <<'AS'
on run argv
set {dom, tag, code} to {item 1 of argv, item 2 of argv, item 3 of argv}
tell application "Safari"
  set fb to missing value
  repeat with w in windows
    repeat with t in tabs of w
      set u to ""
      try
        set u to URL of t
      end try
      if u contains dom then
        set n to ""
        try
          set n to (do JavaScript "window.name" in t)
        end try
        if n is missing value then set n to ""
        if n is tag then return (do JavaScript code in t)
        if fb is missing value and n does not start with "rodokmen-" then set fb to t
      end if
    end repeat
  end repeat
  if fb is missing value then return "NO-TAB"
  return (do JavaScript code in fb)
end tell
end run
AS
)
  else
    out=$(osascript - "$1" "$KARTA" "window.name=\"$KARTA\";$2" 2>"$err" <<'AS'
on run argv
set {dom, tag, code} to {item 1 of argv, item 2 of argv, item 3 of argv}
tell application "Google Chrome"
  set fb to missing value
  repeat with w in windows
    repeat with t in tabs of w
      set u to ""
      try
        set u to URL of t
      end try
      if u contains dom then
        set n to ""
        try
          set n to (execute t javascript "window.name")
        end try
        if n is missing value then set n to ""
        if n is tag then return (execute t javascript code)
        if fb is missing value and n does not start with "rodokmen-" then set fb to t
      end if
    end repeat
  end repeat
  if fb is missing value then return "NO-TAB"
  return (execute fb javascript code)
end tell
end run
AS
)
  fi
  if [[ -s $err ]]; then
    cat "$err" >&2
    grep -qiE 'JavaScript|Apple ?Events|-1743' "$err" && echo "→ $PROHLIZEC: zapni „Povolit JavaScript z událostí Apple“ (Safari: Vývojář; Chrome: Zobrazit → Pro vývojáře) a povol Terminálu ovládat $PROHLIZEC (Nastavení systému → Soukromí a zabezpečení → Automatizace)." >&2
  fi
  rm -f "$err"
  print -r -- "$out"
}

# prohlizec_otevri <adresa> → otevře adresu v nové kartě (v novém okně, když žádné není); kartu označí první prohlizec_js
prohlizec_otevri() {
  if [[ $PROHLIZEC == Safari ]]; then
    osascript - "$1" <<'AS' >/dev/null
on run argv
tell application "Safari"
  if (count of windows) = 0 then
    make new document with properties {URL:(item 1 of argv)}
  else
    tell front window to set current tab to (make new tab with properties {URL:(item 1 of argv)})
  end if
end tell
end run
AS
  else
    osascript - "$1" <<'AS' >/dev/null
on run argv
tell application "Google Chrome"
  if (count of windows) = 0 then
    make new window
    set URL of active tab of front window to (item 1 of argv)
  else
    tell front window to make new tab with properties {URL:(item 1 of argv)}
  end if
end tell
end run
AS
  fi
}
