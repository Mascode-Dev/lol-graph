"""
wiki_api.py — Extraction depuis le Wiki Officiel LoL (wiki.leagueoflegends.com)
=================================================================================
Sources :
  1. MediaWiki API  → Module:ChampionData/data   (Lua → JSON parsé)
     Contient : roles, positions, damage/toughness/control/mobility/utility,
                difficulty, style, adaptivetype, skill names, BE/RP cost, etc.
  2. Page champion  → action=parse → HTML des sections Abilities & Lore
     Contient : descriptions de sorts, lore, relations, régions

Usage :
    python wiki_api.py                              # tous les champions
    python wiki_api.py --champion Aatrox            # un seul
    python wiki_api.py --limit 10 --output test.json
    python wiki_api.py --resume wiki_raw.json       # reprend si interrompu
"""

import requests
import json
import re
import time
import argparse
import logging
from pathlib import Path
from html.parser import HTMLParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
WIKI_BASE   = "https://wiki.leagueoflegends.com/en-us"
API_URL     = f"{WIKI_BASE}/api.php"
HEADERS     = {"User-Agent": "LoL-KnowledgeGraph/2.0 (academic; contact: lol-kg-research)"}
RATE_LIMIT  = 1.2   # secondes entre requêtes

# Noms de champions dont le nom wiki diffère du nom API/affiché
WIKI_NAME_OVERRIDES = {
    "Wukong":          "Wukong",         # apiname = MonkeyKing
    "Nunu & Willump":  "Nunu_&_Willump",
    "Renata Glasc":    "Renata_Glasc",
    "Bel'Veth":        "Bel%27Veth",
    "Cho'Gath":        "Cho%27Gath",
    "Kha'Zix":         "Kha%27Zix",
    "Kog'Maw":         "Kog%27Maw",
    "Rek'Sai":         "Rek%27Sai",
    "Vel'Koz":         "Vel%27Koz",
    "K'Sante":         "K%27Sante",
    "Dr. Mundo":       "Dr._Mundo",
    "Aurelion Sol":    "Aurelion_Sol",
    "Jarvan IV":       "Jarvan_IV",
    "Lee Sin":         "Lee_Sin",
    "Master Yi":       "Master_Yi",
    "Miss Fortune":    "Miss_Fortune",
    "Tahm Kench":      "Tahm_Kench",
    "Twisted Fate":    "Twisted_Fate",
    "Xin Zhao":        "Xin_Zhao",
}

# ─────────────────────────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────────────────────────
def api_get(params: dict) -> dict | None:
    """Appel MediaWiki API avec retry × 3."""
    params.setdefault("format", "json")
    params.setdefault("utf8", "1")
    for attempt in range(3):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            time.sleep(RATE_LIMIT)
            return r.json()
        except Exception as e:
            log.warning(f"API attempt {attempt+1}/3 failed: {e}")
            time.sleep(3 * (attempt + 1))
    return None


def strip_html(html: str) -> str:
    """Enlève les tags HTML et retourne le texte brut."""
    class _P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.chunks = []
        def handle_data(self, data):
            self.chunks.append(data)
    p = _P()
    p.feed(html)
    text = " ".join(p.chunks)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean(s: str) -> str:
    return re.sub(r'\s+', ' ', str(s)).strip() if s else ""


# ─────────────────────────────────────────────────────────────
# STEP 1 — Récupération du Module:ChampionData/data (Lua)
# ─────────────────────────────────────────────────────────────
def fetch_champion_module() -> str | None:
    """
    Récupère le contenu brut du module Lua qui contient TOUTES les données
    de tous les champions. Un seul appel API pour 172 champions.
    """
    log.info("Fetching Module:ChampionData/data from official wiki...")
    data = api_get({
        "action": "query",
        "titles": "Module:ChampionData/data",
        "prop":   "revisions",
        "rvprop": "content",
        "rvslots": "main",
    })
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        revisions = page.get("revisions", [])
        if revisions:
            # MediaWiki API v2 slot format
            content = revisions[0].get("slots", {}).get("main", {}).get("*")
            if not content:
                # Fallback ancien format
                content = revisions[0].get("*", "")
            if content:
                log.info(f"Module fetched: {len(content):,} chars")
                return content
    return None


# ─────────────────────────────────────────────────────────────
# STEP 2 — Parser le Lua en Python dicts
# ─────────────────────────────────────────────────────────────
def parse_lua_module(lua: str) -> dict:
    """
    Parse le module Lua ChampionData en Python dicts.
    Le Lua ressemble à :
        return {
        ["Aatrox"] = {
            ["id"] = 266,
            ["role"] = {"Fighter"},
            ["client_positions"] = {"TOP"},
            ...
        },
        ...
        }
    On utilise des regex robustes car c'est du Lua, pas du JSON.
    """
    champions = {}
    # Trouve chaque bloc champion : ["Name"] = { ... }
    # On isole chaque bloc en comptant les accolades
    champion_pattern = re.compile(r'\["([^"]+)"\]\s*=\s*\{')

    pos = 0
    while True:
        m = champion_pattern.search(lua, pos)
        if not m:
            break

        champ_name = m.group(1)
        # Ignore les sous-tables (stats, etc.) — on les gérera récursivement
        # Vérifie qu'on est au niveau racine (pas imbriqué)
        start = m.end()
        depth = 1
        i = start
        while i < len(lua) and depth > 0:
            if lua[i] == '{':
                depth += 1
            elif lua[i] == '}':
                depth -= 1
            i += 1
        block = lua[start:i-1]

        parsed = parse_lua_block(block)
        if parsed and ("id" in parsed or "apiname" in parsed):
            champions[champ_name] = parsed

        pos = m.start() + 1

    log.info(f"Parsed {len(champions)} champions from Lua module")
    return champions


def parse_lua_block(block: str) -> dict:
    """Parse un bloc Lua { ... } en dict Python (1 niveau + listes)."""
    result = {}

    # Valeurs simples : ["key"] = "value" ou ["key"] = 123
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*"([^"]*)"', block):
        result[m.group(1)] = m.group(2)

    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*(-?\d+(?:\.\d+)?)\b', block):
        key = m.group(1)
        val = m.group(2)
        result[key] = float(val) if '.' in val else int(val)

    # Listes : ["key"] = {"val1", "val2"} ou {"val1"}
    for m in re.finditer(r'\["([^"]+)"\]\s*=\s*\{([^{}]*)\}', block):
        key = m.group(1)
        inner = m.group(2)
        items = [x.strip().strip('"') for x in inner.split(',') if x.strip().strip('"')]
        if items:
            result[key] = items

    # Sous-table stats : ["stats"] = { ... } (récursif 1 niveau)
    stats_m = re.search(r'\["stats"\]\s*=\s*\{', block)
    if stats_m:
        start = stats_m.end()
        depth = 1
        i = start
        while i < len(block) and depth > 0:
            if block[i] == '{': depth += 1
            elif block[i] == '}': depth -= 1
            i += 1
        stats_block = block[stats_m.end():i-1]
        result["stats"] = parse_lua_block(stats_block)

    return result


# ─────────────────────────────────────────────────────────────
# STEP 3 — Page champion : Abilities & Lore via action=parse
# ─────────────────────────────────────────────────────────────
def fetch_champion_page_sections(wiki_page_name: str) -> dict:
    """
    Récupère les sections Abilities et Lore d'une page champion
    via l'API MediaWiki action=parse.
    Retourne {abilities: [...], lore: str, regions: [...], relations: {...}}
    """
    result = {
        "abilities":  [],
        "lore":       "",
        "regions":    [],
        "relations":  {"allies": [], "enemies": [], "mentioned": [], "lore_snippet": ""},
    }

    # 1. Récupère la table des sections
    sections_data = api_get({
        "action":  "parse",
        "page":    wiki_page_name,
        "prop":    "sections",
    })
    if not sections_data or "parse" not in sections_data:
        log.debug(f"No sections data for {wiki_page_name}")
        return result

    sections = sections_data["parse"].get("sections", [])

    # Identifie les indices des sections qui nous intéressent
    ability_idx = None
    lore_idx    = None
    for s in sections:
        title_lower = s.get("line", "").lower()
        if "abilit" in title_lower and ability_idx is None:
            ability_idx = s.get("index")
        if title_lower in ("lore", "background", "story") and lore_idx is None:
            lore_idx = s.get("index")

    # 2. Fetch section Abilities
    if ability_idx:
        ab_data = api_get({
            "action":  "parse",
            "page":    wiki_page_name,
            "prop":    "text",
            "section": ability_idx,
        })
        if ab_data and "parse" in ab_data:
            html = ab_data["parse"].get("text", {}).get("*", "")
            result["abilities"] = parse_abilities_html(html)

    # 3. Fetch section Lore
    if lore_idx:
        lore_data = api_get({
            "action":  "parse",
            "page":    wiki_page_name,
            "prop":    "text",
            "section": lore_idx,
        })
        if lore_data and "parse" in lore_data:
            html = lore_data["parse"].get("text", {}).get("*", "")
            lore_text = strip_html(html)[:3000]
            result["lore"]       = lore_text
            result["regions"]    = extract_regions_from_text(lore_text)
            result["relations"]["lore_snippet"] = lore_text[:800]
            result["relations"]["mentioned"]    = extract_champion_mentions_from_html(html)

    return result


def parse_abilities_html(html: str) -> list[dict]:
    """
    Parse la section HTML des abilities d'une page wiki LoL.
    Structure typique : div.ability-info-stats, h3 avec le nom du sort, etc.
    """
    from html.parser import HTMLParser

    abilities = []
    # Extraire le texte brut puis chercher des patterns
    text = strip_html(html)

    # Pattern slots dans le texte brut
    slot_labels = ["Passive", "Q", "W", "E", "R"]
    # Cherche les blocs par slot
    # Le wiki structure souvent comme: "Passive\nDeathbringer Stance\n[description]"
    slot_pattern = re.compile(
        r'\b(Passive|[QWER])\b\s*[\n\-–—]?\s*([A-Z][^\n]{2,60})\n(.*?)(?=\b(?:Passive|[QWER])\b\s*[\n\-–—]|$)',
        re.DOTALL
    )

    seen_slots = set()
    for m in slot_pattern.finditer(text):
        slot = m.group(1).strip()
        name = clean(m.group(2))
        desc = clean(m.group(3))[:500]

        if slot in seen_slots:
            continue
        seen_slots.add(slot)

        # Extract stats from description
        cooldown_m = re.search(r'[Cc]ooldown[:\s]+([\d\s/\.]+)', desc)
        cost_m     = re.search(r'[Cc]ost[:\s]+([\d\s/\.]+)', desc)
        range_m    = re.search(r'[Rr]ange[:\s]+([\d]+)', desc)

        abilities.append({
            "slot":         slot,
            "name":         name,
            "description":  desc,
            "cooldown_str": cooldown_m.group(1).strip() if cooldown_m else "",
            "cost_str":     cost_m.group(1).strip() if cost_m else "",
            "range":        int(range_m.group(1)) if range_m else None,
        })

    # Fallback si pattern échoue : extrait au moins les noms depuis les headers HTML
    if not abilities:
        abilities = parse_abilities_html_fallback(html)

    return abilities[:5]  # max 5 (Passive + Q + W + E + R)


def parse_abilities_html_fallback(html: str) -> list[dict]:
    """Fallback : extrait les noms de sorts depuis les balises h3/h4/th."""
    abilities = []
    slot_labels = ["Passive", "Q", "W", "E", "R"]

    # Cherche les h3/h4 qui contiennent les noms de sorts
    headers = re.findall(r'<h[234][^>]*>\s*(.*?)\s*</h[234]>', html, re.DOTALL)
    slot_idx = 0
    for header in headers:
        text = strip_html(header).strip()
        if len(text) < 3 or len(text) > 60:
            continue
        if any(skip in text.lower() for skip in ["abilit", "note", "see also", "trivia"]):
            continue
        if slot_idx < len(slot_labels):
            abilities.append({
                "slot": slot_labels[slot_idx],
                "name": text,
                "description": "",
                "cooldown_str": "",
                "cost_str": "",
                "range": None,
            })
            slot_idx += 1
    return abilities


KNOWN_REGIONS = [
    "Demacia", "Noxus", "Freljord", "Piltover", "Zaun", "Ionia",
    "Bilgewater", "Shadow Isles", "Shurima", "Targon", "The Void",
    "Bandle City", "Ixtal", "Runeterra", "Camavor", "Noxus",
]

def extract_regions_from_text(text: str) -> list[str]:
    found = []
    for region in KNOWN_REGIONS:
        if re.search(rf'\b{re.escape(region)}\b', text, re.I):
            found.append(region)
    return list(set(found))


def extract_champion_mentions_from_html(html: str) -> list[str]:
    """Extrait les liens internes wiki qui correspondent à des champions."""
    # Les mentions de champions dans le lore sont souvent des [[links]]
    mentions = re.findall(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]', html)
    mentions += re.findall(r'href="/en-us/([A-Z][a-z_]+)"', html)
    # Nettoie et filtre
    clean_mentions = []
    for m in mentions:
        m = m.replace("_", " ").strip()
        if 2 < len(m) < 30 and m[0].isupper():
            clean_mentions.append(m)
    return list(set(clean_mentions))[:20]


# ─────────────────────────────────────────────────────────────
# STEP 4 — Fusion module + page pour un champion
# ─────────────────────────────────────────────────────────────
def build_champion_record(name: str, module_data: dict, page_data: dict) -> dict:
    """Fusionne les données du module Lua et de la page HTML."""
    m = module_data  # données du module

    # Normalise les positions
    positions = []
    for pos in m.get("client_positions", []):
        p = pos.upper()
        pos_map = {"TOP":"Top","JUNGLE":"Jungle","MID":"Mid",
                   "BOTTOM":"Bot/ADC","SUPPORT":"Support","ADC":"Bot/ADC"}
        positions.append(pos_map.get(p, p.title()))
    # Complète avec external_positions si disponible
    for pos in m.get("external_positions", []):
        p = pos.upper()
        pos_map = {"TOP":"Top","JUNGLE":"Jungle","MID":"Mid",
                   "BOTTOM":"Bot/ADC","SUPPORT":"Support","ADC":"Bot/ADC"}
        mapped = pos_map.get(p, p.title())
        if mapped not in positions:
            positions.append(mapped)
    positions = list(set(positions))

    # Roles
    roles = m.get("role", [])
    if isinstance(roles, str):
        roles = [roles]

    # Noms des sorts depuis le module (slot_i/q/w/e/r)
    spell_names = {
        "Passive": m.get("skill_i", [""])[0] if m.get("skill_i") else "",
        "Q":       m.get("skill_q", [""])[0] if m.get("skill_q") else "",
        "W":       m.get("skill_w", [""])[0] if m.get("skill_w") else "",
        "E":       m.get("skill_e", [""])[0] if m.get("skill_e") else "",
        "R":       m.get("skill_r", [""])[0] if m.get("skill_r") else "",
    }

    # Abilities : enrichit les noms depuis le module si la page n'a pas tout
    abilities = page_data.get("abilities", [])
    for ab in abilities:
        slot = ab.get("slot", "")
        if slot in spell_names and spell_names[slot] and not ab.get("name"):
            ab["name"] = spell_names[slot]

    # Si la page n'a pas donné d'abilities, on crée des shells depuis le module
    if not abilities:
        for slot in ["Passive", "Q", "W", "E", "R"]:
            spell_name = spell_names.get(slot, "")
            if spell_name:
                abilities.append({
                    "slot":         slot,
                    "name":         spell_name,
                    "description":  "",
                    "cooldown_str": "",
                    "cost_str":     "",
                    "range":        None,
                })

    # Stats du module wiki (plus précises que Riot DDragon sur certains points)
    stats_raw = m.get("stats", {})
    stats = {
        "hp":               stats_raw.get("hp_base"),
        "hpperlevel":       stats_raw.get("hp_lvl"),
        "mp":               stats_raw.get("mp_base"),
        "mpperlevel":       stats_raw.get("mp_lvl"),
        "armor":            stats_raw.get("arm_base"),
        "armorperlevel":    stats_raw.get("arm_lvl"),
        "spellblock":       stats_raw.get("mr_base"),
        "spellblockperlevel": stats_raw.get("mr_lvl"),
        "hpregen":          stats_raw.get("hp5_base"),
        "hpregenperlevel":  stats_raw.get("hp5_lvl"),
        "mpregen":          stats_raw.get("mp5_base"),
        "mpregenperlevel":  stats_raw.get("mp5_lvl"),
        "attackdamage":     stats_raw.get("dam_base"),
        "attackdamageperlevel": stats_raw.get("dam_lvl"),
        "attackspeed":      stats_raw.get("as_base"),
        "attackspeedperlevel": stats_raw.get("as_lvl"),
        "movespeed":        stats_raw.get("ms"),
        "attackrange":      stats_raw.get("range"),
        "crit":             stats_raw.get("crit_base", 0),
    }
    # Retire les None
    stats = {k: v for k, v in stats.items() if v is not None}

    return {
        # Identifiants
        "name":         name,
        "id":           str(m.get("apiname", m.get("id", ""))),
        "wiki_id":      m.get("id"),
        "title":        m.get("title", ""),
        # Roles & positions
        "roles":        roles,
        "herotype":     m.get("herotype", ""),      # Riot legacy primary role
        "alttype":      m.get("alttype", ""),        # Riot legacy secondary role
        "positions":    positions,
        # Ressource
        "resource":     m.get("resource", ""),
        # Ratings officiels wiki (1–3 scale, bien plus précis que Riot 0-10)
        "ratings": {
            "damage":     m.get("damage"),
            "toughness":  m.get("toughness"),
            "control":    m.get("control"),
            "mobility":   m.get("mobility"),
            "utility":    m.get("utility", m.get("uility")),  # typo dans le module
            "difficulty": m.get("difficulty"),
            "style":      m.get("style"),           # 0=AA-focused, 100=ability-focused
        },
        # Adaptive damage type
        "adaptivetype": m.get("adaptivetype", ""),
        # Prix
        "cost_be": m.get("be"),
        "cost_rp": m.get("rp"),
        # Patch dernière MàJ
        "last_changed": m.get("changes", ""),
        # Stats
        "stats": stats,
        # Sorts
        "spell_names": spell_names,
        "abilities":   abilities,
        # Lore & régions (depuis la page)
        "lore":      page_data.get("lore", ""),
        "regions":   page_data.get("regions", []),
        "relations": page_data.get("relations", {
            "allies": [], "enemies": [], "mentioned": [], "lore_snippet": ""
        }),
        # Source
        "data_source": "wiki.leagueoflegends.com",
    }


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────
def wiki_name_for(champion_name: str) -> str:
    """Retourne le nom de page wiki pour un champion."""
    if champion_name in WIKI_NAME_OVERRIDES:
        return WIKI_NAME_OVERRIDES[champion_name]
    return champion_name.replace(" ", "_")


def run(args):
    # 1. Fetch le module Lua complet (1 seul appel API pour tous les champions)
    lua_content = fetch_champion_module()
    if not lua_content:
        log.error("Failed to fetch ChampionData module. Exiting.")
        return

    # 2. Parse le Lua
    all_module_data = parse_lua_module(lua_content)
    if not all_module_data:
        log.error("Lua parsing returned 0 champions. Check the module format.")
        return

    # 3. Filtre si --champion spécifié
    if args.champion:
        all_module_data = {k: v for k, v in all_module_data.items()
                          if k.lower() == args.champion.lower()}
        if not all_module_data:
            log.error(f"Champion '{args.champion}' not found in module data.")
            return

    # 4. Limite optionnelle
    names = list(all_module_data.keys())
    if args.limit > 0:
        names = names[:args.limit]

    # 5. Resume
    already_done = {}
    if args.resume and Path(args.resume).exists():
        with open(args.resume, encoding="utf-8") as f:
            existing = json.load(f)
        for c in existing:
            already_done[c["name"]] = c
        log.info(f"Resuming: {len(already_done)} champions already done")

    todo = [n for n in names if n not in already_done]
    log.info(f"Champions to process: {len(todo)}")

    results = list(already_done.values())

    for i, name in enumerate(todo):
        log.info(f"[{i+1}/{len(todo)}] {name}")
        module_data = all_module_data[name]

        # Fetch page sections (abilities + lore)
        wiki_page = wiki_name_for(name)

        if args.module_only:
            page_data = {
                "abilities": [], "lore": "", "regions": [],
                "relations": {"allies":[], "enemies":[], "mentioned":[], "lore_snippet":""}
            }
        else:
            page_data = fetch_champion_page_sections(wiki_page)

        record = build_champion_record(name, module_data, page_data)
        results.append(record)

        log.info(f"  roles={record['roles']} | pos={record['positions']} | "
                 f"abilities={len(record['abilities'])} | regions={record['regions']}")

        # Sauvegarde intermédiaire tous les 15 champions
        if (i + 1) % 15 == 0:
            _save(results, args.output)
            log.info(f"  💾 Auto-saved {len(results)} champions")

    _save(results, args.output)
    log.info(f"\n✅ Done! {len(results)} champions saved to '{args.output}'")
    _print_summary(results)


def _save(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _print_summary(data):
    from collections import Counter
    region_c   = Counter(r for c in data for r in c.get("regions", []))
    role_c     = Counter(r for c in data for r in c.get("roles", []))
    pos_c      = Counter(p for c in data for p in c.get("positions", []))
    with_lore  = sum(1 for c in data if c.get("lore"))
    with_ab    = sum(1 for c in data if c.get("abilities"))

    print(f"\n{'='*55}")
    print(f"📊 WIKI SCRAPE SUMMARY ({len(data)} champions)")
    print(f"{'='*55}")
    print(f"  With lore text  : {with_lore}/{len(data)}")
    print(f"  With abilities  : {with_ab}/{len(data)}")
    print(f"\n  Roles: {dict(role_c.most_common())}")
    print(f"\n  Positions: {dict(pos_c.most_common())}")
    print(f"\n  Regions (top 8): {dict(region_c.most_common(8))}")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(description="LoL Official Wiki API Extractor")
    parser.add_argument("--champion",     type=str,  default="",
                        help="Scrape un seul champion (ex: Aatrox)")
    parser.add_argument("--limit",        type=int,  default=0,
                        help="Limite le nombre de champions (0 = tous)")
    parser.add_argument("--output",       type=str,  default="wiki_raw.json")
    parser.add_argument("--resume",       type=str,  default="",
                        help="Reprend depuis un fichier JSON partiel")
    parser.add_argument("--module-only",  action="store_true",
                        help="Ne fetch que le module Lua (pas les pages HTML) — ultra-rapide")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
