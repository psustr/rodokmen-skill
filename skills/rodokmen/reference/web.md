# Rodinný web – stavba, nastavení, zveřejnění

Web je statický (Astro + vyhledávání Pagefind), data bere z `data/` přes `tools/export_web.py`.
Stránky: úvod (lákadlo, statistiky, zajímavosti, mapa, rody, vějíř), příběh (při víc příbězích rozcestník
`/pribehy/` a stránka každého příběhu `/pribehy/<název>/`), zajímavosti, rody, stránka rodu,
mapa (OpenStreetMap), vějíř přes celou obrazovku s hledáním, seznam předků, zápisy (s výřezem, rámečkem, přepisem
a překladem), stránka osoby, rodiny, „Co hledáme“, výzkumný deník, hledání.

## Příkazy (ve složce `web/`)
| příkaz | co dělá |
|---|---|
| `npm install` | jednou na začátku (stáhne knihovny, ~1 minuta) |
| `npm run data` | převede data do webu (vždy po změně dat; funkční Python 3 vyhledá `scripts/data.mjs`) |
| `npm run build` | sestaví web do `dist/` |
| `npm run nahled` | data + build + náhled na http://localhost:4321 (Ctrl+C ukončí) |
| `npm run dev` | vývojový režim při úpravách vzhledu |
| `npm run nasadit` | data + build + nahrání na Netlify |

Náhled spouštěj na pozadí a uživateli pošli odkaz. Vzhled si ověř sám (snímek obrazovky přes prohlížeč, je-li k dispozici).

## `data/web.json`
```json
{
 "nazev": "Rodokmen Novákových",
 "popis": "Popis pro vyhledávače a sdílení (web je ale noindex).",
 "zapati": "Dohledáno v digitalizovaných matrikách SOA Zámrsk (portál ARON)",
 "kontakt": {"jmeno": "Petrovi", "email": "petr@example.cz"},
 "prihlaseni": {"uvod": "Tenhle web je jen pro rodinu.", "otazka": "Jak se jmenoval pes u babičky v Holicích?", "odpoved": "Alík"},
 "uvod": {"nadpis": "Lákavý nadpis", "odstavce": ["2–3 věty, které chytí"], "foto": "klic_obrazku_ve_vyrezech", "foto_popis": "…"},
 "pribehy": [{"soubor": "novakovi", "menu": "Příběh Nováků", "tlacitko": "Přečíst příběh Nováků"}, {"soubor": "dvorakovi"}],
 "zajimavosti_na_uvodu": [{"nadpis": "Nejstarší předek", "text": "Kovář Jan, asi 1825."}],
 "geni": {"odkaz": "https://www.geni.com/people/…", "odstavce": ["Na Geni máme společný rodokmen…"], "tlacitko": "Otevřít rodokmen na Geni", "pozvanka": "Ještě tam nejste? Napište Petrovi a pošle vám pozvánku."}
}
```
- `kontakt.jmeno` je ve 3. pádě („Napište Petrovi na …“).
- **Přihlášení:** `"kontakt": false` v `prihlaseni` skryje e-mail na veřejné přihlašovací stránce (jinak tam je „Neznáte odpověď? Napište…“).
  Místo otázky může být „Heslo“ a odpověď náhodné heslo (malá písmena a číslice, pomlčky se ignorují) – nejsilnější varianta.
- **Přihlášení:** otázka, na kterou zná odpověď jen rodina (ne snadno dohledatelná na sociálních sítích).
  Odpověď se porovnává bez diakritiky a velkých písmen. Na serveru i v cookie prohlížeče je jen její otisk (SHA-256),
  samotná odpověď se nikam neukládá. Krátkou nebo běžnou odpověď (jméno, obec) ale jde z otisku uhádnout zkoušením,
  proto ať ji uživatel nepoužívá jako heslo jinde. Bez odpovědi nasazení (`npm run nasadit`, `deploy-caprover`)
  skončí chybou; otevřený web jen výslovně přes `"otevreny": true` v `prihlaseni`.
  Je to lehká ochrana proti náhodným návštěvníkům, ne bankovní zabezpečení – citlivé věci na web nepatří.
- `uvod.foto` = klíč obrázku ve `vyrezy/` (ulož přes `vyrez.py`).
- **Portréty:** v `data/dokumenty.json` položka s `"portret": true` (obrázek obličeje, čtvercový výřez ve `vyrezy/`) se ukáže
  jako kulatý avatar u osoby v seznamu předků, ve stromu a u jména na stránce osoby (mezi dokumenty se pak neopakuje).
  Fotky žijících jen se souhlasem (u výchozí osoby stačí její).
- **Fotky z rodinného stromu (Geni, MyHeritage):** export GEDCOM obsahuje odkazy na fotky (`2 FILE https://…`).
  `python3 -I tools/ged_fotky.py <export.ged> <ID výchozí osoby> seznam` ukáže, kdo fotky má, Kekulé předků a u ostatních
  nejbližšího předka s cestou (cesta vede od osoby k předkovi: „otec → otec“ = vnuk). Snímky matrik (soubory pojmenované
  číslem knihy) vynechá. `… stahni <ID> …` stáhne vybrané do `pracovni/ged_foto/` (po jedné, pauza). Pak:
  - **předci:** čtvercový výřez obličeje do `vyrezy/portret_<slug>.jpg` → `dokumenty.json` s `"portret": true` (avatar
    a fotka u jména); celou fotku (ne jen výřez) navíc jako běžný dokument;
  - **ostatní příbuzní** (bez vlastní stránky): `vyrezy/foto_<jméno>.jpg` → dokument u nejbližšího předka, popisek se
    vztahem („vnuk Oldřicha Šustra – syn Josefa Šustra (* 1948)“); všechno je i na stránce `/fotografie/`;
  - **žijící** jen s výslovným souhlasem (děti se souhlasem rodičů) a v popisku jen jméno, rok narození a vztah;
  - ikony a nečitelné náhledy (pod ~100 px, „doc.png“) nedávej; vždy si fotky prohlédni na náhledu (montáž).
  Odkazy v exportu jsou podepsané a po čase vyprší – pak stačí nový export.
- **Příběhy** (`data/pribehy/*.md`, viz `pribehy.md`) se nastavují hlavně ve frontmatter (`title`, `lead`, `rod`, `poradi`,
  `menu`, `tlacitko`). `pribehy` ve `web.json` je nepovinné: pořadí příběhů (`soubor` = název souboru bez `.md`)
  a přepsání `menu`/`tlacitko`/`rod`. `pribehy_menu` = text položky menu při víc příbězích (výchozí „Příběhy“).
  Jeden příběh: v menu jeho `menu` (výchozí „Příběh rodu“), adresa `/pribehy/`. Víc příběhů: v menu rozcestník
  `/pribehy/` s názvy a leady, každý příběh na `/pribehy/<soubor>/`, na úvodu tlačítko ke každému (`tlacitko`,
  jinak „Přečíst: <title>“). Adresa `/pribehy/<soubor>/` funguje i při jediném příběhu (přesměruje na `/pribehy/`),
  takže odkazy v textech vydrží přidání dalšího příběhu. Odkazy mezi příběhy piš `[Příběh Dvořáků](/pribehy/dvorakovi/)`.
- Starý klíč `pribeh` (`{"menu", "rod", "tlacitko"}`) platí dál pro starý `data/pribeh.md`.
  Bez vyplněného `uvod` ukáže úvodní stránka aspoň název a `lead` každého příběhu.
- `npm run data` hlásí `POZOR: nefunkční odkaz …` i v příbězích (osoby, `/zdroj/<klíč>/`, rody, rodiny, `/pribehy/<soubor>/`).
- Šablona `web.json` je prázdná – název nastav hned, jak znáš příjmení výchozí osoby (`kontrola.py` hlásí zbytky ukázky).
- **Rodokmen na Geni / MyHeritage** (`geni`, nepovinné): sekce na konci úvodní stránky – `odkaz` na strom (profil zemřelého
  předka, živí bývají skrytí), `odstavce` (poděkování těm, kdo strom vedou – **jména jen se souhlasem**, raději obecně „naši
  příbuzní“), `tlacitko`, `pozvanka` (výzva pro příbuzné, kteří o stromu nevědí; za ni se doplní `kontakt.email`), `postup`
  (seznam kroků „jak pozvat další příbuzné“, rozbalovací; `postup_nadpis`, `postup_odkaz` na návod služby –
  Geni: https://www.geni.com/blog/how-to-invite-someone-to-your-tree-30171.html). Když
  existuje `data/chyby_geni.md`, je na `/geni/` stránka „Co opravit na Geni“ a z úvodu na ni vede odkaz. Klíče zápisů
  v `obrácených apostrofech` se tam převedou na odkazy na stránky zápisů; první řádek `# …` a komentáře se vynechají.
  Piš ji jako veřejný seznam (bez oslovení a jmen správců), žijící jen jménem a rokem narození. Dopis správci stromu
  (`pracovni/…`) z ní pak jen vychází.
- `citlive_schvaleno`: seznam úryvků textu, které uživatel na webu schválil (např. `["oběsil se ve stodole"]`) –
  `kontrola.py` je pak nehlásí jako `CITLIVÉ`. Úryvek musí obsahovat hlášené slovo; když se text změní, hlásí se znovu.

## Zveřejnění na Netlify (výchozí, zdarma)
1. Uživatel si založí účet na netlify.com (stačí přihlášení přes Google/GitHub) – udělá sám.
2. Přihlášení CLI (otevře prohlížeč) – dej uživateli: `! cd web && npx -y netlify-cli@latest login`.
   Když `!` nejde (cloudové prostředí): `npx -y netlify-cli@latest login --request "Rodokmen"` vypíše odkaz a číslo
   lístku – uživatel odkaz otevře a schválí, pak `npx -y netlify-cli@latest login --check <lístek>`.
3. Založení webu a propojení složky (interaktivní, jednou) – dej uživateli:
   `! cd web && npx -y netlify-cli@latest sites:create` (zvolí tým a název → adresa `https://<název>.netlify.app`),
   případně `npx netlify-cli link`, pokud web už existuje. Je-li uživatel už přihlášený, jde web založit i bez dotazů
   (můžeš spustit sám): `cd web && npx -y netlify-cli@latest sites:create --name <název> --account-slug <tým>`.
   **Windows:** když `!` běží ve Windows PowerShellu 5.1 (`&&` tam nefunguje a `npx` blokuje Execution Policy), ať uživatel
   otevře PowerShell 7 nebo Příkazový řádek, přejde do složky `web` a spustí `npx -y netlify-cli@latest login` (a `sites:create`).
4. Nasazení: `cd web && npm run nasadit` (můžeš spustit sám; vypíše adresu webu).
5. Ověř: otevři adresu **v anonymním okně** → musí se ukázat rodinná přihlašovací otázka; po správné odpovědi web.
   Ukáže-li se místo ní přihlášení k Netlify (401, „Login Redirect“), zdědil web ochranu týmu („Team protection“).
   Uživatel ji vypne v administraci webu: Project configuration → Access & security → Visitor access. Web pak chrání
   rodinná otázka – proto znovu ověř v anonymním okně, že se ukáže.
   Přihlášení zajišťuje Netlify Edge Function `web/netlify/edge-functions/brana.js` (generuje ji export).
Další aktualizace = jen `npm run nasadit`. Vlastní doménu lze nastavit v administraci Netlify.

**Pozor:** „Netlify Drop“ (přetažení složky v prohlížeči) neumí Edge Functions → web by byl bez přihlášení. Nepoužívat.

## Náhled v Claude desktop
Projekt má `.claude/launch.json` – náhled webu v Claude desktop spustí `npm --prefix web run dev` (port 4321). Data se
předtím musí vyexportovat (`cd web && npm run data`). Když náhled nenaběhne (třeba na Windows, kde je `npm` jako `npm.cmd`),
zkus v `launch.json` `"runtimeExecutable": "node"` a `"runtimeArgs": ["web/node_modules/astro/bin/astro.mjs", "dev", "--root", "web"]`
(Astro 7 má spouštěč `astro.mjs`, ne `astro.js`). Server běží jen na tomto počítači – nepřidávej `--host`.

## Vlastní server (pokročilé)
- Docker: `web/Dockerfile` (build Astro → nginx s `nginx.conf` z `nginx.sablona.conf`). Před buildem image vždy `npm run data`.
- CapRover: `npm run deploy-caprover` (vyžaduje nainstalovaný a přihlášený `caprover` CLI).

## Úpravy vzhledu
Styly `web/src/styles/global.css` (barvy v `:root`), rozložení `web/src/layouts/Base.astro`, stránky `web/src/pages/`.
Barvy rodů jsou v `tools/export_web.py` (`LINE_COLORS`) a `tools/fan_chart.py` (`BASE`). Upravuj jen na přání uživatele
a po úpravě zkontroluj web na mobilu i počítači.

## Vějíř jako plakát
`python3 -I tools/fan_chart.py vystupy/` → SVG a HTML (a PNG, je-li nainstalovaný Google Chrome, na Windows i Microsoft Edge) k tisku.

## Aktualizace staršího projektu
Znovu spusť `python3 -I SKILL_DIR/tools/novy_projekt.py <složka projektu>`. Data (`data/`, výřezy) zůstanou, `tools/` se přepíše
a soubory ve `web/`, které se liší od nové šablony, taky – staré verze uloží do `pracovni/zaloha_web_<datum>/` a vypíše jejich seznam.
Upravoval-li jsi s uživatelem vzhled (styly, stránky), převezmi úpravy ze zálohy (porovnej soubory) a ověř web. Pak ve `web/`
`npm install` a `npm run data`. Starou šablonu přihlášení `export_web.py` odmítne s výzvou k aktualizaci.
