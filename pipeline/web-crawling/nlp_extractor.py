"""
nlp_extractor.py v2 — Pipeline NLP pour enrichir les données de sorts LoL
===========================================================================
Analyse les descriptions de sorts pour détecter :
  - Effets CC (17 types : Stun, Root, Slow, Knock Up, Fear, etc.)
  - Types de dégâts (Physical, Magic, True, Mixed)
  - Types de cibles (Single Target, AOE, Line, Cone, Circle, Global...)
  - Mécaniques (Dash, Shield, Heal, Stealth, Execute, Reset, etc.)
  - Tags de playstyle inférés par heuristiques (High_Mobility, Hard_CC, etc.)
  - Relations lore entre champions (via NER spaCy + lookup)

Usage :
    python nlp_extractor.py --input merged.json --output enriched.json --stats
"""

import json
import re
import argparse
import logging
from pathlib import Path
from collections import defaultdict, Counter

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# PATTERNS
# ─────────────────────────────────────────────────────────────

CC_PATTERNS = {
    "Stun":        [r'\bstun(?:ned|s|ning)?\b', r'\bbriefly immobilize\b'],
    "Root":        [r'\broot(?:ed|s|ing)?\b', r'\bsnare(?:d|s)?\b', r'\bimmobilize(?:d)?\b'],
    "Slow":        [r'\bslow(?:ed|s|ing)?\b', r'\breduced? (?:movement )?speed\b'],
    "Knock_Up":    [r'\bknock(?:ed|s)? up\b', r'\bknockup\b', r'\bairborne\b',
                   r'\blaunch(?:es|ed)? (?:them )?into the air\b'],
    "Knock_Back":  [r'\bknock(?:ed|s)? (?:them )?back\b', r'\bknockback\b'],
    "Knock_Aside": [r'\bknock(?:ed|s)? (?:them )?aside\b', r'\bdisplace(?:s|d)?\b'],
    "Silence":     [r'\bsilence(?:d|s)?\b', r'\bprevents? (?:from )?cast(?:ing)?\b'],
    "Blind":       [r'\bblind(?:ed|s|ness)?\b', r'\bmisses? all (?:basic )?attacks\b'],
    "Fear":        [r'\bfear(?:ed|s|ing)?\b', r'\bfleeing\b', r'\bflees?\b'],
    "Taunt":       [r'\btaunt(?:ed|s|ing)?\b', r'\bforced? to attack\b'],
    "Charm":       [r'\bcharm(?:ed|s|ing)?\b', r'\bwalks? toward\b'],
    "Sleep":       [r'\bsleep(?:s|ing)?\b', r'\bput to sleep\b'],
    "Suppression": [r'\bsuppress(?:ed|es|ion)?\b', r'\bchanneled? suppress\b'],
    "Polymorph":   [r'\bpolymorph(?:ed|s)?\b'],
    "Pull":        [r'\bpull(?:ed|s|ing)? (?:to|toward|back)\b',
                   r'\bdrag(?:s|ged|ging)? (?:to|toward)\b'],
    "Grounded":    [r'\bground(?:ed)?\b', r'\bprevents? dashes?\b'],
    "Nearsight":   [r'\bnearsight(?:ed)?\b', r'\breduced? vision range\b'],
}

DAMAGE_PATTERNS = {
    "Physical": [r'\bphysical damage\b', r'\b\(?total AD\)?\b', r'\b\(?bonus AD\)?\b',
                 r'\battack damage\b'],
    "Magic":    [r'\bmagic(?:al)? damage\b', r'\b\(?AP\)?\b', r'\bability power\b'],
    "True":     [r'\btrue damage\b'],
    "Mixed":    [r'\bboth physical and magic\b'],
}

TARGET_PATTERNS = {
    "Single_Target":  [r'\bsingle[- ]target\b', r'\ban? (?:enemy |target )?champion\b',
                       r'\bnearest (?:enemy|champion)\b', r'\bchosen target\b'],
    "AOE":            [r'\bnearby (?:enemies|champions)\b',
                       r'\ball (?:enemies|champions) (?:in|within|around)\b',
                       r'\barea of effect\b', r'\bsurround(?:ing)?\b',
                       r'\bwithin \d+ (?:units|range)\b'],
    "Line":           [r'\bin a (?:straight )?line\b', r'\bskillshot\b',
                       r'\bfires? (?:a )?(?:bolt|beam|missile)\b'],
    "Cone":           [r'\bcone\b', r'\bfan[- ]shaped\b', r'\bin front of\b'],
    "Circle":         [r'\bcircle\b', r'\baround (?:him|her|them)\b', r'\bsphere\b'],
    "Arc":            [r'\barc\b', r'\bboomerang\b'],
    "Global":         [r'\bglobal\b', r'\banywhere on the map\b'],
    "Point_and_Click":[r'\bpoint[- ]and[- ]click\b', r'\bcannot be dodged\b',
                       r'\bauto[- ]target\b'],
}

MECHANIC_PATTERNS = {
    "Shield":        [r'\bshield(?:s|ed|ing)?\b', r'\babsorbs? damage\b', r'\bbarrier\b'],
    "Heal":          [r'\bheal(?:s|ed|ing|th)?\b', r'\brestore(?:s|d)? health\b',
                     r'\blife ?steal\b', r'\bomni[- ]?vamp\b'],
    "Dash":          [r'\bdash(?:es|ed|ing)?\b', r'\bleap(?:s|ed|ing)?\b',
                     r'\bjump(?:s|ed|ing)?\b', r'\bcharge(?:s|ed|ing)?\b'],
    "Blink":         [r'\bblink(?:s|ed|ing)?\b', r'\bteleport(?:s|ed|ing)?\b',
                     r'\bwink(?:s|ed)?\b'],
    "Stealth":       [r'\binvisib(?:le|ility|le)\b', r'\bcamouflage\b', r'\bstealth\b'],
    "Summon":        [r'\bsummon(?:s|ed|ing)?\b', r'\bspawn(?:s|ed|ing)?\b',
                     r'\bcreates? (?:a|an) \w+\b'],
    "Transform":     [r'\btransform(?:s|ed|ing)?\b', r'\bmorph(?:s|ed|ing)?\b',
                     r'\bshift(?:s|ed|ing)? forms?\b'],
    "Execute":       [r'\bexecut(?:e|es|ed|ion)\b', r'\binstantly kill(?:s)?\b',
                     r'\bfinish(?:es|ed|ing)?\b'],
    "Mark":          [r'\bmark(?:s|ed|ing)?\b', r'\bbrand(?:s|ed)?\b'],
    "Tether":        [r'\btether(?:s|ed|ing)?\b', r'\bchain(?:s|ed|ing)?\b',
                     r'\blink(?:s|ed|ing)?\b'],
    "Empowered_AA":  [r'\bempowered? (?:basic )?attack\b', r'\benhanced? auto\b',
                     r'\bnext basic attack\b'],
    "Passive_Buff":  [r'\bpassively\b', r'\boutside of combat\b', r'\bwhile in combat\b'],
    "Toggle":        [r'\btoggle(?:d|s)?\b', r'\bactivate or deactivate\b'],
    "Recast":        [r'\brecast\b', r'\bcan be re-?cast\b'],
    "Channel":       [r'\bchannel(?:s|ed|ing)?\b', r'\bcharging\b'],
    "Reset":         [r'\breset(?:s|ting)?\b', r'\brefresh(?:es|ed)?\b'],
    "Wall":          [r'\bwall\b', r'\bterrain\b', r'\bblocks? (?:movement|path)\b'],
    "Zone_Control":  [r'\bzone\b', r'\bdenies? (?:area|ground)\b'],
    "Shred":         [r'\bshred(?:s|ding)?\b', r'\breduces? (?:armor|magic resist)\b'],
    "Slow_Aura":     [r'\baura\b', r'\bpersistent slow\b'],
}

PLAYSTYLE_HEURISTICS = [
    # (tag, condition_fn(mechanic_counts, cc_counts, target_counts))
    ("High_Mobility",    lambda mc, cc, tc: mc["Dash"] + mc["Blink"] >= 2),
    ("Stealth_Capable",  lambda mc, cc, tc: mc["Stealth"] >= 1),
    ("Self_Sustain",     lambda mc, cc, tc: mc["Heal"] >= 2),
    ("Shield_Ability",   lambda mc, cc, tc: mc["Shield"] >= 1),
    ("Summoner",         lambda mc, cc, tc: mc["Summon"] >= 1),
    ("Execute_Ability",  lambda mc, cc, tc: mc["Execute"] >= 1),
    ("Shapeshifter",     lambda mc, cc, tc: mc["Transform"] >= 1),
    ("Channel_Heavy",    lambda mc, cc, tc: mc["Channel"] >= 2),
    ("Reset_Mechanic",   lambda mc, cc, tc: mc["Reset"] >= 1),
    ("Hard_CC",          lambda mc, cc, tc: any(cc.get(x, 0) > 0 for x in
                         ["Stun","Suppression","Knock_Up","Knock_Back","Fear","Charm","Sleep","Polymorph"])),
    ("High_CC",          lambda mc, cc, tc: len([x for x in cc if cc[x] > 0]) >= 3),
    ("Soft_CC_Focus",    lambda mc, cc, tc: cc["Slow"] >= 2 and
                         not any(cc.get(x, 0) for x in ["Stun","Suppression","Knock_Up"])),
    ("AOE_Focus",        lambda mc, cc, tc: tc["AOE"] >= 3),
    ("Dive_Threat",      lambda mc, cc, tc: mc["Dash"] >= 1 and mc["Execute"] >= 1),
    ("Poke_Pattern",     lambda mc, cc, tc: tc["Line"] >= 2 and mc["Dash"] == 0),
    ("Zone_Control",     lambda mc, cc, tc: mc["Wall"] + mc["Zone_Control"] >= 1),
    ("AA_Enhancer",      lambda mc, cc, tc: mc["Empowered_AA"] >= 2),
    ("Global_Presence",  lambda mc, cc, tc: tc["Global"] >= 1),
]


# ─────────────────────────────────────────────────────────────
# ANALYSE D'UN SORT
# ─────────────────────────────────────────────────────────────
def analyze_ability(ability: dict) -> dict:
    """Enrichit un sort avec les tags CC, dégâts, cibles et mécaniques."""
    # Concatène description + tooltip pour maximiser la couverture
    text = " ".join(filter(None, [
        ability.get("description", ""),
        ability.get("tooltip", ""),
    ])).lower()

    def match_patterns(patterns_dict):
        found = []
        for tag, pats in patterns_dict.items():
            if any(re.search(p, text) for p in pats):
                found.append(tag)
        return found

    enriched = dict(ability)
    enriched["cc_effects"]    = match_patterns(CC_PATTERNS)
    enriched["damage_types"]  = match_patterns(DAMAGE_PATTERNS)
    enriched["target_types"]  = match_patterns(TARGET_PATTERNS)
    enriched["mechanics"]     = match_patterns(MECHANIC_PATTERNS)
    return enriched


# ─────────────────────────────────────────────────────────────
# PLAYSTYLE TAGS
# ─────────────────────────────────────────────────────────────
def infer_playstyle(abilities: list[dict]) -> list[str]:
    """Infère les tags de playstyle à partir de l'agrégat des sorts."""
    mc = Counter()
    cc = Counter()
    tc = Counter()
    for ab in abilities:
        for m in ab.get("mechanics", []):
            mc[m] += 1
        for c in ab.get("cc_effects", []):
            cc[c] += 1
        for t in ab.get("target_types", []):
            tc[t] += 1

    tags = []
    for tag, condition in PLAYSTYLE_HEURISTICS:
        try:
            if condition(mc, cc, tc):
                tags.append(tag)
        except Exception:
            pass
    return tags


# ─────────────────────────────────────────────────────────────
# RELATIONS LORE (spaCy + lookup)
# ─────────────────────────────────────────────────────────────
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None and SPACY_AVAILABLE:
        try:
            _nlp = spacy.load("en_core_web_sm")
            log.info("spaCy 'en_core_web_sm' loaded")
        except OSError:
            log.warning("spaCy model not found — run: python -m spacy download en_core_web_sm")
    return _nlp


def infer_lore_relations(champion: dict, known_names: set) -> dict:
    """
    Enrichit les relations lore d'un champion :
    - Cherche les mentions de noms de champions dans le lore
    - Tente de classifier allies/enemies par contexte
    """
    current = champion["name"]
    existing = champion.get("relations", {
        "allies": [], "enemies": [], "mentioned": [], "lore_snippet": ""
    })

    lore = champion.get("lore", "")
    ab_text = " ".join(
        (ab.get("description","") + " " + ab.get("tooltip",""))
        for ab in champion.get("abilities", [])
    )
    full_text = lore + " " + ab_text

    # spaCy NER — détecte les entités PERSON dans le lore
    spacy_mentions = set()
    nlp = get_nlp()
    if nlp and lore:
        doc = nlp(lore[:2000])
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG") and ent.text in known_names:
                spacy_mentions.add(ent.text)

    # Lookup direct des noms connus dans le texte complet
    lookup_mentions = set()
    for name in known_names:
        if name != current and re.search(rf'\b{re.escape(name)}\b', full_text):
            lookup_mentions.add(name)

    all_mentioned = spacy_mentions | lookup_mentions

    # Classifier allies / enemies par fenêtre contextuelle
    new_allies  = list(existing.get("allies", []))
    new_enemies = list(existing.get("enemies", []))
    new_mentioned = list(existing.get("mentioned", []))

    ALLY_WORDS  = r'\b(ally|allies|friend|partner|sibling|sister|brother|love|with|alongside|companion|trusted)\b'
    ENEMY_WORDS = r'\b(enemy|enemies|rival|foe|oppose|fight|hunts?|kill|defeat|clash|against|battles?)\b'

    for name in all_mentioned:
        if name in new_allies or name in new_enemies:
            continue
        window = re.search(
            rf'(.{{0,80}})\b{re.escape(name)}\b(.{{0,80}})',
            full_text, re.I
        )
        if window:
            ctx = (window.group(1) + window.group(2)).lower()
            if re.search(ALLY_WORDS, ctx):
                new_allies.append(name)
            elif re.search(ENEMY_WORDS, ctx):
                new_enemies.append(name)
            elif name not in new_mentioned:
                new_mentioned.append(name)
        else:
            if name not in new_mentioned:
                new_mentioned.append(name)

    return {
        "allies":       list(set(new_allies)),
        "enemies":      list(set(new_enemies)),
        "mentioned":    list(set(new_mentioned)),
        "lore_snippet": existing.get("lore_snippet", lore[:600]),
    }


# ─────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────
def enrich_champion(champion: dict, known_names: set) -> dict:
    enriched = dict(champion)

    # 1. Enrichir les sorts (abilities)
    enriched_abilities = [analyze_ability(ab) for ab in champion.get("abilities", [])]
    enriched["abilities"] = enriched_abilities

    # 2. Agréger les tags au niveau champion
    enriched["champion_cc_effects"]   = list({cc for ab in enriched_abilities for cc in ab.get("cc_effects", [])})
    enriched["champion_damage_types"] = list({d  for ab in enriched_abilities for d  in ab.get("damage_types", [])})
    enriched["champion_mechanics"]    = list({m  for ab in enriched_abilities for m  in ab.get("mechanics", [])})

    # 3. Playstyle tags
    enriched["playstyle_tags"] = infer_playstyle(enriched_abilities)

    # 4. Relations lore
    enriched["relations"] = infer_lore_relations(enriched, known_names)

    return enriched


def enrich_all(data: list[dict]) -> list[dict]:
    known_names = {c["name"] for c in data}
    log.info(f"NLP enrichment: {len(data)} champions, {len(known_names)} known names")

    enriched = []
    for i, champ in enumerate(data):
        if i % 25 == 0:
            log.info(f"  [{i+1}/{len(data)}] {champ.get('name','?')}")
        enriched.append(enrich_champion(champ, known_names))

    log.info("NLP enrichment complete")
    return enriched


# ─────────────────────────────────────────────────────────────
# STATS RAPPORT
# ─────────────────────────────────────────────────────────────
def print_stats(data: list[dict]):
    cc_freq    = Counter(cc for c in data for cc in c.get("champion_cc_effects", []))
    mech_freq  = Counter(m  for c in data for m  in c.get("champion_mechanics", []))
    style_freq = Counter(t  for c in data for t  in c.get("playstyle_tags", []))
    has_rel    = sum(1 for c in data if any([
        c.get("relations",{}).get("allies"),
        c.get("relations",{}).get("enemies"),
    ]))

    print(f"\n{'='*55}")
    print(f"📊 NLP ENRICHMENT STATS ({len(data)} champions)")
    print(f"{'='*55}")
    print(f"\n  CC Effects (top 10):")
    for cc, n in cc_freq.most_common(10):
        bar = "█" * (n // 3)
        print(f"    {cc:<20} {n:>3}  {bar}")
    print(f"\n  Mechanics (top 10):")
    for m, n in mech_freq.most_common(10):
        bar = "█" * (n // 3)
        print(f"    {m:<20} {n:>3}  {bar}")
    print(f"\n  Playstyle tags:")
    for t, n in style_freq.most_common():
        bar = "█" * (n // 4)
        print(f"    {t:<22} {n:>3}  {bar}")
    print(f"\n  Champions with lore relations: {has_rel}/{len(data)}")
    print(f"{'='*55}\n")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LoL NLP Enrichment Pipeline v2")
    parser.add_argument("--input",  default="data/processed/enriched.json")
    parser.add_argument("--output", default="data/processed/enriched.json")
    parser.add_argument("--stats",  action="store_true")
    args = parser.parse_args()

    if not Path(args.input).exists():
        log.error(f"Input not found: {args.input} — run merge.py first")
        return

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    if not SPACY_AVAILABLE:
        log.warning("spaCy not available — lore relation NER disabled (regex only)")

    enriched = enrich_all(data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Saved to {args.output}")

    if args.stats:
        print_stats(enriched)


if __name__ == "__main__":
    main()
