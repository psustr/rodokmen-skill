# Rozpracováno – skill lanove-rejstriky (větev `lanove-rejstriky`)

Stav 2026-10-30. Před sloučením / PR tento soubor smazat.

## Hotovo
- `skills/lanove-rejstriky/SKILL.md` – návrh postupu (bez otestování).
- Lokálně zpřístupněno symlinkem `~/.claude/skills/lanove-rejstriky` → tato složka.

## Zbývá
1. **Nástroj `skills/rodokmen/tools/lanove.py`** (příkazy `hledat "Obec"`, `info`, `nahledy`, `snimek`, `link`, `svazek`
   – tak, jak je popisuje SKILL.md).
   - MZA ARON je stejný software jako ARON Zámrsk → převzít `aron_img.py` (`volume`, `fetch_image`) s API
     `https://www.mza.cz/aron/api/aron` a hlavičkou User-Agent (bez ní mza.cz odmítá).
   - Kniha: `GET /apu/<id>` → `digitalObjects[0].files` typu `TILE` s `referencedFile` = URL `.dzi` (iipsrv Deep Zoom).
   - Fond „MZA v Brně: Lánové rejstříky“ (D 1), série „Úřední knihy“ apu `f8ff279b-aa5f-448e-a55c-7c8fea9a432d`
     (372 knih). Obce knihy jsou entity `J_G` v poli `result` (JSON v řetězci), NE v `description` →
     `listview?listType=SEARCH` s FTXF na `description` vrací 0. Výpis dětí série přes `listview` s filtrem
     `parent` vrátil HTTP 400 – správný tvar dotazu zjistit z JS front-endu `https://www.mza.cz/aron/`
     (alternativa: jednorázově projít 372 knih a uložit index obec → kniha do cache).
   - Fond má přílohy (PDF „popis katastrů“, místní rejstřík) – možná zdroj indexu obcí.
2. **Test** na projektu `~/Work/Rodokmen`: Vít Šustr (č. 1024, Skřípov, ∞ 1664, † 1695) v D 1 kn. 182
   „Panství Klášterní Hradisko, Šebetov, Vřesovice“, apu `3b67c3e6-aedb-4702-a125-6bde11c4ce1e`, 151 snímků
   (sn. 2 = titul „Closter Radisch Gütter“). Podklady: `~/Work/Rodokmen/pracovni/pom_vit/archiv.md`, `lr.py`.
3. Podle testu upravit SKILL.md; zmínit nástroj v tabulce nástrojů `skills/rodokmen/SKILL.md`
   a v `reference/portaly.md` (MZA); zvednout verzi (plugin.json, VERZE, README – viz CLAUDE.md).
4. Rozhodnout: push na vlastní Git, nebo PR autorovi (sarsonj/rodokmen-skill).

## Pozor
- mza.cz 30. 10. uprostřed práce přestalo odpovídat (časové limity) – možná omezení po řadě dotazů. Šetrně, po jednom.
