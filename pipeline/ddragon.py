"""
ddragon.py — Extraction depuis Riot Data Dragon API
=====================================================
Récupère pour TOUS les champions :
  - Stats complètes (hp, armor, ms, attackrange, etc.)
  - Sorts détaillés (cooldown, coût, range, tooltip par rank)
  - Passive
  - Skins (avec chromas)
  - Lore & tips (ally/enemy)
  - Blurb

Tout ça en HTTP direct, sans scraping — c'est l'API officielle Riot.

Usage :
    python ddragon.py                          # latest patch, tous les champions
    python ddragon.py --version 16.5.1         # patch spécifique
    python ddragon.py --champion Aatrox        # un seul champion
    python ddragon.py --output ddragon_raw.json
"""

import requests
import json
import time
import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

DDRAGON_BASE = "https://ddragon.leagueoflegends.com"
HEADERS      = {"User-Agent": "LoL-KnowledgeGraph/2.0"}
RATE_LIMIT   = 0.3   # DDragon est un CDN — on peut aller plus vite
MAX_WORKERS  = 6     # threads parallèles pour les détails par champion


# ─────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────
def get_json(url: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"Attempt {attempt+1}/{retries} failed [{url}]: {e}")
            time.sleep(2 * (attempt + 1))
    return None


def strip_html_tags(text: str) -> str:
    import re
    return re.sub(r'<[^>]+>', '', text or "").strip()


# ─────────────────────────────────────────────────────────────
# STEP 1 — Dernière version
# ─────────────────────────────────────────────────────────────
def get_latest_version() -> str:
    data = get_json(f"{DDRAGON_BASE}/api/versions.json")
    if data:
        return data[0]
    return "16.5.1"


# ─────────────────────────────────────────────────────────────
# STEP 2 — Liste des champions (summary)
# ─────────────────────────────────────────────────────────────
def get_champion_list(version: str) -> dict:
    """Retourne le dict {championId: {...}} du endpoint champion.json."""
    url  = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/champion.json"
    data = get_json(url)
    if data:
        log.info(f"DDragon champion list: {len(data['data'])} champions (v{version})")
        return data["data"]
    return {}


# ─────────────────────────────────────────────────────────────
# STEP 3 — Détails complets par champion
# ─────────────────────────────────────────────────────────────
def get_champion_detail(champion_id: str, version: str) -> dict | None:
    """
    Fetch le JSON complet d'un champion depuis DDragon.
    Endpoint: /cdn/{version}/data/en_US/champion/{ChampionId}.json
    Contient: spells, passive, skins, lore, allytips, enemytips, stats
    """
    url  = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/champion/{champion_id}.json"
    data = get_json(url)
    if not data:
        return None
    # Le JSON a la structure {"data": {"ChampionId": {...}}}
    champions = data.get("data", {})
    if champion_id in champions:
        return champions[champion_id]
    # Fallback : premier élément
    if champions:
        return list(champions.values())[0]
    return None


# ─────────────────────────────────────────────────────────────
# STEP 4 — Normalisation des données
# ─────────────────────────────────────────────────────────────
def normalize_champion(raw: dict) -> dict:
    """
    Normalise un champion DDragon en un format propre et cohérent
    avec le format wiki_api.py.
    """
    # ── Stats ──
    s = raw.get("stats", {})
    stats = {
        "hp":                   s.get("hp"),
        "hpperlevel":           s.get("hpperlevel"),
        "mp":                   s.get("mp"),
        "mpperlevel":           s.get("mpperlevel"),
        "movespeed":            s.get("movespeed"),
        "armor":                s.get("armor"),
        "armorperlevel":        s.get("armorperlevel"),
        "spellblock":           s.get("spellblock"),
        "spellblockperlevel":   s.get("spellblockperlevel"),
        "attackrange":          s.get("attackrange"),
        "hpregen":              s.get("hpregen"),
        "hpregenperlevel":      s.get("hpregenperlevel"),
        "mpregen":              s.get("mpregen"),
        "mpregenperlevel":      s.get("mpregenperlevel"),
        "attackdamage":         s.get("attackdamage"),
        "attackdamageperlevel": s.get("attackdamageperlevel"),
        "attackspeed":          s.get("attackspeed"),
        "attackspeedperlevel":  s.get("attackspeedperlevel"),
        "crit":                 s.get("crit", 0),
    }
    stats = {k: v for k, v in stats.items() if v is not None}

    # ── Spells ──
    slot_map = {0: "Q", 1: "W", 2: "E", 3: "R"}
    abilities = []
    for i, spell in enumerate(raw.get("spells", [])):
        # Cooldowns par rank
        cooldown = spell.get("cooldown", [])
        cooldown_burn = spell.get("cooldownBurn", "")
        cost = spell.get("cost", [])
        cost_burn = spell.get("costBurn", "0")
        range_list = spell.get("range", [])
        range_burn = spell.get("rangeBurn", "")

        abilities.append({
            "slot":         slot_map.get(i, f"Spell{i}"),
            "id":           spell.get("id", ""),
            "name":         spell.get("name", ""),
            "description":  strip_html_tags(spell.get("description", "")),
            "tooltip":      strip_html_tags(spell.get("tooltip", "")),
            "maxrank":      spell.get("maxrank", 5),
            "cooldown":     cooldown,
            "cooldown_burn": cooldown_burn,
            "cost":         cost,
            "cost_burn":    cost_burn,
            "cost_type":    spell.get("costType", ""),
            "range":        range_list,
            "range_burn":   range_burn,
        })

    # ── Passive ──
    passive_raw = raw.get("passive", {})
    passive = {
        "name":        passive_raw.get("name", ""),
        "description": strip_html_tags(passive_raw.get("description", "")),
    } if passive_raw else {}

    # ── Skins ──
    skins = [
        {
            "id":      str(sk.get("id", "")),
            "num":     sk.get("num", 0),
            "name":    sk.get("name", "default"),
            "chromas": sk.get("chromas", False),
        }
        for sk in raw.get("skins", [])
    ]

    # ── Info ratings ──
    info = raw.get("info", {})

    return {
        # Identifiants
        "name":         raw.get("name", ""),
        "id":           raw.get("id", ""),
        "key":          raw.get("key", ""),
        "title":        raw.get("title", ""),
        # Roles (DDragon = tags)
        "tags":         raw.get("tags", []),
        "partype":      raw.get("partype", ""),
        # Lore & tips
        "lore":         raw.get("lore", ""),
        "blurb":        raw.get("blurb", ""),
        "allytips":     raw.get("allytips", []),
        "enemytips":    raw.get("enemytips", []),
        # Abilities
        "abilities":    abilities,
        "passive":      passive,
        # Skins
        "skins":        skins,
        # Stats
        "stats":        stats,
        # Info ratings (Riot 0-10 scale)
        "info": {
            "attack":     info.get("attack"),
            "defense":    info.get("defense"),
            "magic":      info.get("magic"),
            "difficulty": info.get("difficulty"),
        },
        # Meta
        "version":      raw.get("version", ""),
        "data_source":  "ddragon.leagueoflegends.com",
    }


# ─────────────────────────────────────────────────────────────
# STEP 5 — Fetch parallèle de tous les champions
# ─────────────────────────────────────────────────────────────
def fetch_all_champions(version: str, filter_name: str = "", limit: int = 0) -> list[dict]:
    """Fetch les détails de tous les champions en parallèle."""
    champion_list = get_champion_list(version)
    if not champion_list:
        return []

    ids = list(champion_list.keys())
    if filter_name:
        ids = [i for i in ids if i.lower() == filter_name.lower()
               or champion_list[i]["name"].lower() == filter_name.lower()]
    if limit > 0:
        ids = ids[:limit]

    log.info(f"Fetching details for {len(ids)} champions (parallel, {MAX_WORKERS} workers)...")

    results = []
    failed  = []

    def _fetch(champ_id):
        raw = get_champion_detail(champ_id, version)
        if raw:
            return normalize_champion(raw)
        return None

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch, cid): cid for cid in ids}
        done = 0
        for future in as_completed(futures):
            cid = futures[future]
            result = future.result()
            if result:
                results.append(result)
            else:
                failed.append(cid)
                log.warning(f"Failed: {cid}")
            done += 1
            if done % 20 == 0:
                log.info(f"  Progress: {done}/{len(ids)}")

    if failed:
        log.warning(f"Failed champions ({len(failed)}): {failed}")

    log.info(f"✅ DDragon fetch complete: {len(results)} champions")
    return results


# ─────────────────────────────────────────────────────────────
# RAPPORT
# ─────────────────────────────────────────────────────────────
def print_summary(data: list[dict]):
    from collections import Counter
    tag_c  = Counter(t for c in data for t in c.get("tags", []))
    res_c  = Counter(c.get("partype", "") for c in data)
    with_lore  = sum(1 for c in data if c.get("lore"))
    with_spell = sum(1 for c in data if c.get("abilities"))
    with_skin  = sum(1 for c in data if c.get("skins"))
    total_skins = sum(len(c.get("skins", [])) for c in data)

    print(f"\n{'='*55}")
    print(f"📊 DDRAGON SUMMARY ({len(data)} champions)")
    print(f"{'='*55}")
    print(f"  With lore    : {with_lore}/{len(data)}")
    print(f"  With spells  : {with_spell}/{len(data)}")
    print(f"  With skins   : {with_skin}/{len(data)} ({total_skins} total skins)")
    print(f"\n  Tags: {dict(tag_c.most_common())}")
    print(f"\n  Resources (top 8): {dict(res_c.most_common(8))}")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LoL Data Dragon Extractor")
    parser.add_argument("--version",   type=str, default="",
                        help="Version DDragon (ex: 16.5.1). Défaut: latest")
    parser.add_argument("--champion",  type=str, default="",
                        help="Champion unique (ex: Aatrox)")
    parser.add_argument("--limit",     type=int, default=0)
    parser.add_argument("--output",    type=str, default="ddragon_raw.json")
    parser.add_argument("--stats",     action="store_true")
    args = parser.parse_args()

    version = args.version or get_latest_version()
    log.info(f"Using DDragon version: {version}")

    results = fetch_all_champions(version, args.champion, args.limit)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    log.info(f"✅ Saved to {args.output}")

    if args.stats:
        print_summary(results)


if __name__ == "__main__":
    main()
