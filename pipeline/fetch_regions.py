"""
fetch_regions.py v2 — Injecte les régions lore dans enriched.json
===================================================================
Stratégie : map statique complète basée sur le lore officiel Riot.
Les régions sont stables (changent très rarement) donc une map
hardcodée est la solution la plus robuste et la plus rapide.

En bonus : tente de lire le champ "region" depuis wiki_raw.json si présent.

Usage :
    python fetch_regions.py                          # patch enriched.json + TTL
    python fetch_regions.py --dry-run                # affiche sans modifier
    python fetch_regions.py --wiki wiki_raw.json     # enrichit depuis wiki_raw si dispo
"""

import json
import argparse
import logging
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# MAP COMPLÈTE champion → régions (source: lore officiel Riot)
# Certains champions appartiennent à plusieurs régions
# ─────────────────────────────────────────────────────────────
CHAMPION_REGIONS: dict[str, list[str]] = {
    # DEMACIA
    "Fiora":        ["Demacia"],
    "Galio":        ["Demacia"],
    "Garen":        ["Demacia"],
    "Jarvan IV":    ["Demacia"],
    "Kayle":        ["Demacia"],
    "Lux":          ["Demacia"],
    "Morgana":      ["Demacia"],
    "Poppy":        ["Demacia"],
    "Quinn":        ["Demacia"],
    "Shyvana":      ["Demacia"],
    "Sona":         ["Demacia"],
    "Vayne":        ["Demacia"],
    "Xin Zhao":     ["Demacia"],
    "Lucian":       ["Demacia"],
    "Sylas":        ["Demacia"],

    # NOXUS
    "Ambessa":      ["Noxus"],
    "Cassiopeia":   ["Noxus"],
    "Darius":       ["Noxus"],
    "Draven":       ["Noxus"],
    "Katarina":     ["Noxus"],
    "LeBlanc":      ["Noxus"],
    "Mordekaiser":  ["Noxus"],
    "Riven":        ["Noxus"],
    "Samira":       ["Noxus"],
    "Sion":         ["Noxus"],
    "Swain":        ["Noxus"],
    "Talon":        ["Noxus"],
    "Vladimir":     ["Noxus"],
    "Kled":         ["Noxus"],
    "Mel":          ["Noxus"],

    # FRELJORD
    "Ashe":         ["Freljord"],
    "Braum":        ["Freljord"],
    "Gragas":       ["Freljord"],
    "Lissandra":    ["Freljord"],
    "Nunu & Willump": ["Freljord"],
    "Olaf":         ["Freljord"],
    "Ornn":         ["Freljord"],
    "Sejuani":      ["Freljord"],
    "Trundle":      ["Freljord"],
    "Tryndamere":   ["Freljord"],
    "Udyr":         ["Freljord"],
    "Volibear":     ["Freljord"],
    "Anivia":       ["Freljord"],
    "Aurora":       ["Freljord"],
    "Briar":        ["Freljord"],

    # PILTOVER
    "Caitlyn":      ["Piltover"],
    "Camille":      ["Piltover"],
    "Corki":        ["Piltover"],
    "Ezreal":       ["Piltover"],
    "Heimerdinger": ["Piltover"],
    "Jayce":        ["Piltover"],
    "Orianna":      ["Piltover"],
    "Seraphine":    ["Piltover"],
    "Vi":           ["Piltover"],

    # ZAUN
    "Blitzcrank":   ["Zaun"],
    "Dr. Mundo":    ["Zaun"],
    "Ekko":         ["Zaun"],
    "Jinx":         ["Zaun"],
    "Renata Glasc": ["Zaun"],
    "Singed":       ["Zaun"],
    "Twitch":       ["Zaun"],
    "Urgot":        ["Zaun"],
    "Viktor":       ["Zaun"],
    "Warwick":      ["Zaun"],
    "Zac":          ["Zaun"],
    "Zeri":         ["Zaun"],

    # IONIA
    "Ahri":         ["Ionia"],
    "Akali":        ["Ionia"],
    "Irelia":       ["Ionia"],
    "Ivern":        ["Ionia"],
    "Jhin":         ["Ionia"],
    "Karma":        ["Ionia"],
    "Kayn":         ["Ionia"],
    "Kennen":       ["Ionia"],
    "Lee Sin":      ["Ionia"],
    "Lillia":       ["Ionia"],
    "Master Yi":    ["Ionia"],
    "Rakan":        ["Ionia"],
    "Sett":         ["Ionia"],
    "Shen":         ["Ionia"],
    "Syndra":       ["Ionia"],
    "Varus":        ["Ionia"],
    "Wukong":       ["Ionia"],
    "Xayah":        ["Ionia"],
    "Yasuo":        ["Ionia"],
    "Yone":         ["Ionia"],
    "Zed":          ["Ionia"],
    "Hwei":         ["Ionia"],
    "Naafiri":      ["Ionia"],  # Noxus/Ionia — primarily Ionia-adjacent
    "Smolder":      ["Ionia"],

    # BILGEWATER
    "Gangplank":    ["Bilgewater"],
    "Graves":       ["Bilgewater"],
    "Illaoi":       ["Bilgewater"],
    "Miss Fortune": ["Bilgewater"],
    "Nautilus":     ["Bilgewater"],
    "Nilah":        ["Bilgewater"],
    "Pyke":         ["Bilgewater"],
    "Tahm Kench":   ["Bilgewater"],
    "Twisted Fate": ["Bilgewater"],
    "Fizz":         ["Bilgewater"],

    # SHADOW ISLES
    "Gwen":         ["Shadow Isles"],
    "Hecarim":      ["Shadow Isles"],
    "Kalista":      ["Shadow Isles"],
    "Karthus":      ["Shadow Isles"],
    "Maokai":       ["Shadow Isles"],
    "Mordekaiser":  ["Noxus", "Shadow Isles"],
    "Senna":        ["Shadow Isles"],
    "Thresh":       ["Shadow Isles"],
    "Vex":          ["Shadow Isles"],
    "Viego":        ["Shadow Isles"],
    "Yorick":       ["Shadow Isles"],
    "Elise":        ["Shadow Isles"],
    "Nocturne":     ["Shadow Isles"],

    # SHURIMA
    "Akshan":       ["Shurima"],
    "Amumu":        ["Shurima"],
    "Azir":         ["Shurima"],
    "Nasus":        ["Shurima"],
    "Rammus":       ["Shurima"],
    "Renekton":     ["Shurima"],
    "Sivir":        ["Shurima"],
    "Skarner":      ["Shurima"],
    "Taliyah":      ["Shurima"],
    "Xerath":       ["Shurima"],
    "Naafiri":      ["Shurima"],

    # TARGON
    "Aphelios":     ["Targon"],
    "Aurelion Sol": ["Targon"],
    "Diana":        ["Targon"],
    "Leona":        ["Targon"],
    "Pantheon":     ["Targon"],
    "Soraka":       ["Targon"],
    "Taric":        ["Targon"],
    "Zoe":          ["Targon"],

    # THE VOID
    "Bel'Veth":     ["The Void"],
    "Cho'Gath":     ["The Void"],
    "Kai'Sa":       ["The Void", "Shurima"],
    "Kassadin":     ["The Void"],
    "Kha'Zix":      ["The Void"],
    "Kog'Maw":      ["The Void"],
    "Malzahar":     ["The Void"],
    "Rek'Sai":      ["The Void"],
    "Vel'Koz":      ["The Void"],

    # BANDLE CITY
    "Corki":        ["Bandle City"],
    "Heimerdinger": ["Bandle City"],
    "Kennen":       ["Bandle City"],
    "Lulu":         ["Bandle City"],
    "Rumble":       ["Bandle City"],
    "Teemo":        ["Bandle City"],
    "Tristana":     ["Bandle City"],
    "Veigar":       ["Bandle City"],
    "Yuumi":        ["Bandle City"],
    "Ziggs":        ["Bandle City"],
    "Gnar":         ["Bandle City"],
    "Mega Gnar":    ["Bandle City"],
    "Kled & Skaarl": ["Bandle City"],

    # IXTAL
    "Milio":        ["Ixtal"],
    "Neeko":        ["Ixtal"],
    "Nidalee":      ["Ixtal"],
    "Qiyana":       ["Ixtal"],
    "Rengar":       ["Ixtal"],
    "Zyra":         ["Ixtal"],

    # SHURIMA (suite)
    "Aatrox":       ["Shurima"],

    # NOXUS (suite)
    "Rell":         ["Noxus"],

    # RUNETERRA (pas de région fixe / errants / multiples)
    "Alistar":      ["Runeterra"],
    "Annie":        ["Runeterra"],
    "Bard":         ["Runeterra"],
    "Brand":        ["Runeterra"],
    "Fiddlesticks": ["Runeterra"],
    "Janna":        ["Runeterra"],
    "Jax":          ["Runeterra"],
    "Kindred":      ["Runeterra"],
    "Malphite":     ["Runeterra"],
    "Nami":         ["Runeterra"],
    "Ryze":         ["Runeterra"],
    "Shaco":        ["Runeterra"],
    "Singed":       ["Runeterra"],   # also Zaun
    "Teemo":        ["Bandle City"], # override above
    "Vel'Koz":      ["The Void"],
    "Zilean":       ["Runeterra"],
    "Zoe":          ["Targon"],
    "Evelynn":      ["Runeterra"],
    "Twitch":       ["Zaun"],
    "Warwick":      ["Zaun"],
    "K'Sante":      ["Shurima"],
    "Zaahen":       ["Runeterra"],
    "Yunara":       ["Runeterra"],
}

# Résout les doublons dans la map (un champion peut être listé deux fois)
# On garde la dernière entrée comme référence principale mais on merge les régions
_MERGED: dict[str, list[str]] = {}
for champ, regions in CHAMPION_REGIONS.items():
    if champ in _MERGED:
        for r in regions:
            if r not in _MERGED[champ]:
                _MERGED[champ].append(r)
    else:
        _MERGED[champ] = list(regions)
CHAMPION_REGIONS = _MERGED


# ─────────────────────────────────────────────────────────────
# ENRICHISSEMENT DEPUIS wiki_raw.json (si dispo)
# Le module Lua contient parfois un champ "region" ou "herotype"
# ─────────────────────────────────────────────────────────────
def enrich_from_wiki_raw(wiki_path: str) -> dict[str, list[str]]:
    """
    Tente de lire les régions depuis wiki_raw.json.
    Le module Lua ChampionData a un champ 'region' sur certains champions.
    """
    extra = {}
    if not Path(wiki_path).exists():
        return extra

    with open(wiki_path, encoding="utf-8") as f:
        wiki_data = json.load(f)

    for champ in wiki_data:
        name = champ.get("name", "")
        # Le champ region peut être une liste ou une string dans le module Lua
        raw_regions = champ.get("regions") or champ.get("region") or []
        if isinstance(raw_regions, str):
            raw_regions = [raw_regions]
        if raw_regions:
            extra[name] = raw_regions

    log.info(f"wiki_raw provided regions for {len(extra)} champions")
    return extra


# ─────────────────────────────────────────────────────────────
# PATCH
# ─────────────────────────────────────────────────────────────
def patch_enriched(data: list[dict], extra_regions: dict[str, list[str]]) -> list[dict]:
    """Injecte les régions dans chaque champion."""
    patched   = 0
    not_found = []

    for champ in data:
        name = champ.get("name", "")

        # Priorité : hardcoded map → wiki_raw → déjà présent
        regions = (
            CHAMPION_REGIONS.get(name)
            or extra_regions.get(name)
            or champ.get("regions")
            or []
        )

        if regions:
            champ["regions"] = regions
            patched += 1
        else:
            not_found.append(name)

    log.info(f"Regions patched: {patched}/{len(data)}")
    if not_found:
        log.warning(f"No region found for {len(not_found)} champions: {not_found}")

    return data


# ─────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────
def print_stats(data: list[dict]):
    region_c  = Counter(r for c in data for r in c.get("regions", []))
    no_region = [c["name"] for c in data if not c.get("regions")]
    multi     = [c["name"] for c in data if len(c.get("regions", [])) > 1]

    print(f"\n{'='*55}")
    print(f"🗺️  REGION DISTRIBUTION ({len(data)} champions)")
    print(f"{'='*55}")
    for region, count in sorted(region_c.items(), key=lambda x: -x[1]):
        bar = "█" * count
        print(f"  {region:<18} {count:>3}  {bar}")
    print(f"\n  Multi-region champions ({len(multi)}): {multi}")
    if no_region:
        print(f"\n  ⚠️  No region ({len(no_region)}): {no_region}")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fetch and Inject Regions into enriched.json")
    parser.add_argument("--enriched", default="data/processed/enriched.json")
    parser.add_argument("--ttl",      default="lol_ontology_v3.ttl")
    parser.add_argument("--wiki",     default="data/raw/wiki_raw.json",
                        help="wiki_raw.json pour enrichir (optionnel)")
    parser.add_argument("--no-ttl",   action="store_true")
    parser.add_argument("--stats",    action="store_true")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    if not Path(args.enriched).exists():
        log.error(f"Not found: {args.enriched}")
        return

    with open(args.enriched, encoding="utf-8") as f:
        data = json.load(f)

    # Enrichit depuis wiki_raw si dispo
    extra = enrich_from_wiki_raw(args.wiki)

    # Patch
    data = patch_enriched(data, extra)
    print_stats(data)

    if args.dry_run:
        log.info("Dry run — no files written")
        return

    # Sauvegarde
    with open(args.enriched, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"✅ enriched.json updated")

    # Régénère TTL
    if not args.no_ttl:
        try:
            import merge
            merge.generate_ttl(data, args.ttl)
            log.info(f"✅ TTL regenerated → {args.ttl}")
        except ImportError:
            log.warning("merge.py not found — run: python merge.py --ttl-only")


if __name__ == "__main__":
    main()
