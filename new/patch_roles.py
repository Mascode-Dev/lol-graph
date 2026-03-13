"""
patch_roles.py — Patch les rôles depuis ddragon_raw.json → enriched.json → TTL
================================================================================
Problème : merge.py prend wiki.roles en priorité, mais le wiki ne retourne
les rôles que pour ~46 champions. DDragon a les tags pour TOUS.

Ce script :
  1. Lit ddragon_raw.json (champ "tags" par champion)
  2. Patch enriched.json avec les rôles DDragon
  3. Régénère lol_ontology_v3.ttl

Usage :
    python patch_roles.py
    python patch_roles.py --dd ddragon_raw.json --enriched enriched.json
"""

import json
import re
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Tags DDragon valides (correspondent exactement aux individus dans le TTL)
VALID_ROLES = {"Fighter", "Tank", "Mage", "Assassin", "Marksman", "Support"}


def build_roles_map(dd_path: str) -> dict[str, list[str]]:
    """Construit {champion_name: [roles]} depuis ddragon_raw.json."""
    with open(dd_path, encoding="utf-8") as f:
        dd_data = json.load(f)

    roles_map = {}
    for champ in dd_data:
        name = champ.get("name", "")
        tags = [t for t in champ.get("tags", []) if t in VALID_ROLES]
        if name and tags:
            roles_map[name] = tags

    log.info(f"DDragon roles map: {len(roles_map)} champions avec tags")
    return roles_map


def patch_enriched(enriched_path: str, roles_map: dict[str, list[str]]) -> list[dict]:
    with open(enriched_path, encoding="utf-8") as f:
        data = json.load(f)

    patched    = 0
    not_found  = []

    for champ in data:
        name   = champ.get("name", "")
        roles  = roles_map.get(name)

        if roles:
            champ["roles"] = roles
            patched += 1
        else:
            not_found.append(name)

    log.info(f"Roles patched: {patched}/{len(data)}")
    if not_found:
        log.warning(f"No DDragon tags for: {not_found}")

    return data


def print_stats(data: list[dict]):
    from collections import Counter
    role_c    = Counter(r for c in data for r in c.get("roles", []))
    no_role   = [c["name"] for c in data if not c.get("roles")]
    multi     = [(c["name"], c["roles"]) for c in data if len(c.get("roles", [])) > 1]

    print(f"\n{'='*55}")
    print(f"📊 ROLE DISTRIBUTION ({len(data)} champions)")
    print(f"{'='*55}")
    for role, n in sorted(role_c.items(), key=lambda x: -x[1]):
        bar = "█" * (n // 2)
        print(f"  {role:<12} {n:>3}  {bar}")
    print(f"\n  Multi-role champions ({len(multi)}):")
    for name, roles in sorted(multi):
        print(f"    {name}: {roles}")
    if no_role:
        print(f"\n  ⚠️  No role: {no_role}")
    print(f"{'='*55}\n")


def main():
    parser = argparse.ArgumentParser(description="Patch roles in enriched.json from DDragon tags")
    parser.add_argument("--dd",       default="ddragon_raw.json")
    parser.add_argument("--enriched", default="enriched.json")
    parser.add_argument("--ttl",      default="lol_ontology_v3.ttl")
    parser.add_argument("--no-ttl",   action="store_true")
    parser.add_argument("--stats",    action="store_true")
    args = parser.parse_args()

    if not Path(args.dd).exists():
        log.error(f"Not found: {args.dd} — run ddragon.py first")
        return
    if not Path(args.enriched).exists():
        log.error(f"Not found: {args.enriched} — run merge.py first")
        return

    roles_map = build_roles_map(args.dd)
    data      = patch_enriched(args.enriched, roles_map)

    if args.stats:
        print_stats(data)
    else:
        # Affiche quand même le résumé de base
        from collections import Counter
        role_c = Counter(r for c in data for r in c.get("roles", []))
        print(f"\nRoles: { {r: n for r, n in sorted(role_c.items(), key=lambda x: -x[1])} }\n")

    with open(args.enriched, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"✅ enriched.json updated → {args.enriched}")

    if not args.no_ttl:
        try:
            import merge
            merge.generate_ttl(data, args.ttl)
            log.info(f"✅ TTL regenerated → {args.ttl}")
        except ImportError:
            log.warning("merge.py not found — run: python merge.py --ttl-only")


if __name__ == "__main__":
    main()
