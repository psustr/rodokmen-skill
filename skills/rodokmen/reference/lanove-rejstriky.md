# Lánové rejstříky (Morava 1656–1679)

Součást skillu **rodokmen** (projekt, data a pravidla jsou jeho – `data/STAV.md`, `research_log.md`, „doc“ jen
z přečteného snímku, nejistoty „(?)“). Staré pojmy vysvětli (lán, láník, pustý grunt).

**Nástroje:** `tools/lanove.py` (hledání knihy, info, snímek, odkaz, svazek) a `tools/aron_obrazovka.sh` (snímek uloží
**prohlížeč**: snímky ARONu leží na stejném obrázkovém serveru MZA jako matriky, skript je proto otevře v kartě matrik
MZA (Acta Publica) tamním prohlížečem obrázků v dočasném panelu, počká na vykreslení a uloží plátno jako „Uložit obrázek
jako“; žádné stahování dlaždic skriptem, žádné cizí hlavičky). Funguje i se **skrytým oknem a zamčenou obrazovkou** –
uživatel může dál pracovat. Velikost panelu `RODOKMEN_ARON_PANEL` (výchozí 1600x1000 → ~3200×2000 px na Retině);
přiblížení oblasti `… x0,y0,x1,y1` (zlomky 0–1 snímku) dá vyšší rozlišení. Metadata knih stahuje `lanove.py` s poctivou
identifikací. Index všech 372 knih fondu je sdílený pro všechny projekty v `~/.cache/rodokmen-lanove/` (první `hledat`
ho vytvoří, ~15 min, jen popisy s pauzou). Snímky drž i ve sdíleném archivu (např. `~/Work/rodokmen-archiv/
lanove-rejstriky/<sign>_<panství>/`), ať se ze stejné knihy nestahuje znovu.
(Prohlížeč ARONu samotný ve skryté kartě nevykresluje a ovládá se jen skutečnou myší – proto ho skript nepoužívá.)

## Co to je a co z toho zjistíme
- Soupis poddanské (rustikální) půdy na Moravě po třicetileté válce, kvůli daním. **Jen Morava** (ne Čechy – tam berní rula
  1654; ne Slezsko). Originály v **MZA Brno, fond D 1 Lánové rejstříky**, 1 kniha ≈ 1 panství/statek, digitalizováno, volně online.
- Dvě vlny: **1. lánová vizitace 1656–1658** a **revizitace 1669–1679** (v jedné knize často obě; v revizitaci bývá
  vedle sebe „starý“ hospodář z 1. vizitace a nový – to je nejcennější: kdo po kom grunt převzal).
- Po obcích, v každé obci hospodáři po řadě: **jméno hospodáře**, druh usedlosti (láník / celoláník, pololáník,
  čtvrtláník, podsedník, chalupník, zahradník; něm. Ganzlahner, Halblahner, Viertler, Gärtner, Häusler), výměra
  (lány, měřice / „Metzen“ výsevu, role, louky), **osedlý × pustý** grunt („öde“, „pustý“, „ganz verödet“), občas
  řemeslo, „neu angesessen“ (nově osedlý), vypálení (1663 Turci/Tataři).
- Zapsán je **jen hospodář** (držitel gruntu) – ne manželka, děti, podruzi, čeleď. Jméno bez věku.
- Využití: (1) dokáže, že předek (nebo rod) v obci seděl už 1656–1679 i tam, kde matriky začínají později;
  (2) usedlost a její velikost (sociální postavení); (3) posloupnost na gruntu → otec/syn/vdova/přiženěný.
  Shoda jména **není** důkaz příbuzenství – stejnojmenných hospodářů bývá v obci víc; propoj přes grunt a matriky.

## Postup
1. **Obec a doba.** Z dat projektu: obec a roky nejstaršího předka (např. sňatek 1664, děti 1671–1683).
   Má smysl, když žil (nebo jeho otec) v letech 1656–1679 na Moravě.
2. **Najdi knihu:** `python3 -I tools/lanove.py hledat "Obec"` → kniha (apu id), panství, roky, počet snímků, obce z popisu.
   **Popisy obcí v ARONu nejsou úplné** (u knihy Konice jen Konice, Křemenec, Runářov) – nic? Zkus sousední obce,
   panství, kam obec tehdy patřila (vrchnost, klášter), německé jméno; pak obec ověř na snímcích knihy.
   Zapiš svazek: `python3 -I tools/lanove.py svazek <apu>` (do `data/svazky.json`, klíč „lr“ + 6 znaků apu).
3. **Najdi obec v knize.** Kniha nemá rejstřík a obce nejdou abecedně. Ulož snímky po jednom
   (`python3 -I tools/lanove.py snimek <apu> <n> pracovni/lr/<sign>/<n>.jpg`, ~15 s + pauza) a z nich si udělej
   tablo náhledů a výřezy hlaviček – velký nadpis obce („Dorff …“, „Markt …“, „Gemein …“, „Ves …“). Obec mívá 1–6 snímků; první vizitace bývá v knize zvlášť od revizitace –
   hledej obec v obou. Do deníku zapisuj prošlé snímky i neúspěšné.
4. **Přečti hospodáře obce celé** (ne jen „naše“ jméno): pořadí, jméno, druh usedlosti, výměra, osedlý/pustý,
   poznámky, v revizitaci i „starý“ hospodář. Pozor na německou kurentu (Schuster × Fischer, Müller × Miller,
   Barthl/Bartl), latinská/česká/německá podoba téhož jména, „Wittib“ / „vdova“ = vdova po hospodáři.
   Nejisté čtení si ověř `tools/overit.py` (zápis na dvě poloviny).
5. **Zapiš** (přes `tools/zapis.py`, formát viz `rodokmen/reference/data.md`):
   - `zaznamy.json`: `druh: "J"`, klíč `obec_lanovy_rejstrik_prijmeni_rok` (rok vizitace, např. 1657 / 1675),
     `odkaz` z `lanove.py link <apu> <n>`; výřez (`vyrez.py`) a rámeček (`ramecek.py`) jako u matrik.
   - `prepisy.json`: `orig` po sloupcích (`[Pořadí] [Hospodář] [Usedlost] [Výměra] [Stav] [Pozn.]`), `cs` česky
     s vysvětlením („pololáník = sedlák s polovinou lánu, střední statek“).
   - u předka v `osoby.py` fakt typu `"hospodář (pololáník) ve Skřípově 1657, 1675"`; `st` předka se tím nemění.
6. **Navaž na grunt.** Pořadí hospodářů v obci často odpovídá pozdějším číslům domů a pořadí v pozemkových
   (gruntovních) knihách. Další krok: pozemková kniha obce (MZA fond „Pozemkové knihy“ nebo SOA / ZA Opava),
   první zápisy u gruntu – převod z otce na syna, vdova, přiženění; pak tereziánský katastr (1713–1757) a
   josefský katastr (1785–1789) se čísly domů. Spojení drž jako hypotézu (`HYPOTEZY`), dokud ho nedoloží
   pozemková kniha nebo matrika (čp. v matrice od ~1770).
7. **Řekni uživateli příběh:** jak velký grunt předek měl, zda byl pustý a kdo ho osadil, kdo byli sousedé,
   zda je rod v obci už 1656 (nejstarší doklad rodu v obci).

## Tipy a pasti
- Kniha = panství z doby vizitace; panství se pak měnila (koupě, slučování) – v 18. stol. bývá obec jinde.
- Pustý grunt s cizím jménem v revizitaci často znamená, že ho mezitím někdo osadil – hledej jméno v matrice
  téže doby (sňatek, kmotrovství).
- Snímky ukládá jen prohlížeč, jeden po druhém (společný zámek s MZA). Když archiv přestane odpovídat, přestaň a zkus
  to za hodiny – neobcházej to jinou sítí ani skriptem.
- Edice a pomůcky (tištěné, knihovny/Kramerius): F. Matějek, *Lánové rejstříky olomouckého kraje z let 1675–1678*;
  MZA má k fondu nový inventář s místním rejstříkem (D. Štaud 2017) – přílohy fondu v ARON.
