"""
merge.py — Fusion Wiki + DDragon + NLP → JSON enrichi + TTL Protégé
=====================================================================
Stratégie de merge (priorité) :
  1. Wiki officiel  → roles, positions, ratings (damage/toughness/control/mobility/utility),
                       style, adaptivetype, spell_names, lore, régions, last_changed
  2. DDragon        → stats précises, spells détaillés (cooldown/coût/range par rank),
                       passive, skins, blurb, allytips/enemytips, key Riot
  3. NLP enrichment → cc_effects, damage_types, mechanics, playstyle_tags, relations lore

Le résultat = lol_ontology_v2.ttl directement importable dans Protégé.

Usage :
    python merge.py                                         # merge tout
    python merge.py --wiki wiki_raw.json --dd ddragon_raw.json
    python merge.py --ttl-only --enriched enriched.json    # régénère juste le TTL
    python merge.py --no-nlp                                # skip NLP (rapide)
"""

import json
import re
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# MERGE
# ─────────────────────────────────────────────────────────────
def merge(wiki_data: list[dict], dd_data: list[dict]) -> list[dict]:
    """
    Fusionne les données Wiki et DDragon.
    Wiki est la source principale pour les métadonnées.
    DDragon est la source principale pour les stats et sorts.
    """
    # Index par nom (normalisé)
    def norm(s): return re.sub(r"[^a-z]", "", (s or "").lower())

    wiki_idx = {norm(c["name"]): c for c in wiki_data}
    dd_idx   = {norm(c["name"]): c for c in dd_data}

    all_names = set(wiki_idx) | set(dd_idx)
    log.info(f"Merging: {len(wiki_idx)} wiki + {len(dd_idx)} ddragon → {len(all_names)} unique")

    results = []
    for name_key in sorted(all_names):
        wiki = wiki_idx.get(name_key, {})
        dd   = dd_idx.get(name_key, {})

        # Nom d'affichage = DDragon ou Wiki
        display_name = dd.get("name") or wiki.get("name") or name_key

        # ── Abilities : DDragon en priorité (plus complet), fallback Wiki ──
        dd_abilities   = dd.get("abilities", [])
        wiki_abilities = wiki.get("abilities", [])

        # Fusionne : DDragon fournit cooldown/range/cost, Wiki fournit les descriptions
        # si DDragon les a déjà (avec tooltip) on garde DDragon, sinon on merge
        if dd_abilities:
            abilities = dd_abilities
            # Enrichit avec les descriptions wiki si DDragon a des descriptions vides
            wiki_ab_idx = {ab.get("slot"): ab for ab in wiki_abilities}
            for ab in abilities:
                if not ab.get("description") and ab.get("slot") in wiki_ab_idx:
                    ab["description"] = wiki_ab_idx[ab["slot"]].get("description", "")
        else:
            abilities = wiki_abilities

        # ── Roles : Wiki en priorité (plus précis) ──
        roles = wiki.get("roles") or dd.get("tags") or []

        # ── Positions : Wiki (client_positions est officiel) ──
        positions = wiki.get("positions") or []

        # ── Ratings : Wiki uniquement (DDragon n'a que attack/defense/magic 0-10) ──
        wiki_ratings = wiki.get("ratings", {})
        dd_info      = dd.get("info", {})
        ratings = {
            # Wiki ratings (1-3 scale, précis)
            "damage":     wiki_ratings.get("damage"),
            "toughness":  wiki_ratings.get("toughness"),
            "control":    wiki_ratings.get("control"),
            "mobility":   wiki_ratings.get("mobility"),
            "utility":    wiki_ratings.get("utility"),
            "difficulty": wiki_ratings.get("difficulty") or dd_info.get("difficulty"),
            "style":      wiki_ratings.get("style"),
            # DDragon legacy ratings (0-10)
            "riot_attack":   dd_info.get("attack"),
            "riot_defense":  dd_info.get("defense"),
            "riot_magic":    dd_info.get("magic"),
        }
        ratings = {k: v for k, v in ratings.items() if v is not None}

        # ── Stats : DDragon en priorité ──
        stats = dd.get("stats") or wiki.get("stats") or {}

        # ── Lore : DDragon (plus complet en général) ──
        lore = dd.get("lore") or wiki.get("lore") or ""

        # ── Régions : Wiki ──
        regions = wiki.get("regions") or []

        # ── Relations : Wiki ──
        relations = wiki.get("relations") or {
            "allies": [], "enemies": [], "mentioned": [], "lore_snippet": ""
        }
        # Ajoute le lore snippet DDragon si pas déjà présent
        if not relations.get("lore_snippet") and lore:
            relations["lore_snippet"] = lore[:600]

        merged = {
            # Identifiants
            "name":         display_name,
            "id":           dd.get("id") or wiki.get("id") or "",
            "key":          dd.get("key") or str(wiki.get("wiki_id", "")),
            "title":        dd.get("title") or wiki.get("title") or "",
            # Classification
            "roles":        roles,
            "positions":    positions,
            "resource":     wiki.get("resource") or dd.get("partype") or "",
            "adaptivetype": wiki.get("adaptivetype") or "",
            # Ratings
            "ratings":      ratings,
            # Stats
            "stats":        stats,
            # Sorts
            "abilities":    abilities,
            "passive":      dd.get("passive") or {},
            "spell_names":  wiki.get("spell_names") or {},
            # Skins
            "skins":        dd.get("skins") or [],
            # Lore & tips
            "lore":         lore,
            "blurb":        dd.get("blurb") or "",
            "allytips":     dd.get("allytips") or [],
            "enemytips":    dd.get("enemytips") or [],
            # Régions & relations
            "regions":      regions,
            "relations":    relations,
            # Meta
            "last_changed": wiki.get("last_changed") or "",
            "cost_be":      wiki.get("cost_be"),
            "cost_rp":      wiki.get("cost_rp"),
            "version":      dd.get("version") or "",
            # NLP (rempli après par nlp_extractor)
            "champion_cc_effects":   [],
            "champion_damage_types": [],
            "champion_mechanics":    [],
            "playstyle_tags":        [],
        }
        results.append(merged)

    log.info(f"Merge complete: {len(results)} champions")
    return results


# ─────────────────────────────────────────────────────────────
# TTL GENERATOR
# ─────────────────────────────────────────────────────────────
def safe_uri(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(s))

def esc(s) -> str:
    if s is None: return '""'
    s = re.sub(r'<[^>]+>', '', str(s))
    s = s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','')
    return f'"{s}"'

def xsd_d(v): return f'"{v}"^^xsd:double'
def xsd_i(v): return f'"{v}"^^xsd:integer'
def xsd_b(v): return f'"{str(v).lower()}"^^xsd:boolean'

# ── Vocabulaire contrôlé ──
ROLES      = ["Fighter","Mage","Assassin","Marksman","Support","Tank"]
RESOURCES  = ["Mana","Energy","Blood_Well","Courage","Crimson_Rush","Ferocity",
              "Flow","Fury","Grit","Heat","None","Rage","Shield"]
REGIONS    = ["Demacia","Noxus","Freljord","Piltover","Zaun","Ionia","Bilgewater",
              "Shadow_Isles","Shurima","Targon","The_Void","Bandle_City","Ixtal",
              "Runeterra","Camavor"]
POSITIONS  = ["Top","Jungle","Mid","Bot_ADC","Support"]
CC_LIST    = ["Stun","Root","Slow","Knock_Up","Knock_Back","Knock_Aside","Silence",
              "Blind","Fear","Taunt","Charm","Sleep","Suppression","Polymorph",
              "Pull","Grounded","Nearsight"]
MECHANICS  = ["Shield","Heal","Dash","Blink","Stealth","Summon","Transform","Execute",
              "Mark","Tether","Empowered_AA","Passive_Buff","Toggle","Recast",
              "Channel","Reset","Wall","Zone_Control","Shred","Slow_Aura"]
PLAYSTYLE  = ["High_Mobility","Stealth_Capable","Self_Sustain","Shield_Ability",
              "Summoner","Execute_Ability","Shapeshifter","Channel_Heavy","Reset_Mechanic",
              "Hard_CC","High_CC","Soft_CC_Focus","AOE_Focus","Dive_Threat",
              "Poke_Pattern","Zone_Control_Tag","AA_Enhancer","Global_Presence"]

# Normalisation régions (texte → URI)
REGION_NORM = {
    "shadow isles": "Shadow_Isles",
    "the void":     "The_Void",
    "bandle city":  "Bandle_City",
}
def region_uri(r):
    lo = r.lower().strip()
    return REGION_NORM.get(lo, safe_uri(r))

def pos_uri(p):
    return {"Bot/ADC":"Bot_ADC","ADC":"Bot_ADC","Bottom":"Bot_ADC"}.get(p, safe_uri(p))


ONTOLOGY_HEADER = '''\
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:   <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:    <http://www.w3.org/2002/07/owl#> .
@prefix xsd:    <http://www.w3.org/2001/XMLSchema#> .
@prefix lol:    <http://leagueoflegends.knowledge/ontology#> .
@prefix champ:  <http://leagueoflegends.knowledge/champion/> .
@prefix spell:  <http://leagueoflegends.knowledge/spell/> .
@prefix skin:   <http://leagueoflegends.knowledge/skin/> .
@prefix role:   <http://leagueoflegends.knowledge/role/> .
@prefix res:    <http://leagueoflegends.knowledge/resource/> .
@prefix region: <http://leagueoflegends.knowledge/region/> .
@prefix pos:    <http://leagueoflegends.knowledge/position/> .
@prefix cc:     <http://leagueoflegends.knowledge/cc_effect/> .
@prefix mech:   <http://leagueoflegends.knowledge/mechanic/> .
@prefix style:  <http://leagueoflegends.knowledge/playstyle/> .

<http://leagueoflegends.knowledge/ontology>
    a owl:Ontology ;
    rdfs:label "League of Legends Knowledge Graph v3"@en ;
    rdfs:comment "Sources: wiki.leagueoflegends.com (officiel) + DDragon + NLP enrichment"@en ;
    owl:versionInfo "3.0.0" .

# ══════════════════════════════════════════════════════════════
# CLASSES
# ══════════════════════════════════════════════════════════════

lol:Champion       a owl:Class ; rdfs:label "Champion"@en ;
    rdfs:comment "A playable character in League of Legends."@en .

lol:Spell          a owl:Class ; rdfs:label "Spell"@en .
lol:ActiveSpell    a owl:Class ; rdfs:subClassOf lol:Spell ; rdfs:label "Active Spell"@en ;
    rdfs:comment "Keybind ability: Q, W, E, or R."@en .
lol:PassiveAbility a owl:Class ; rdfs:subClassOf lol:Spell ; rdfs:label "Passive Ability"@en .

lol:Skin           a owl:Class ; rdfs:label "Skin"@en .
lol:Role           a owl:Class ; rdfs:label "Role"@en ;
    rdfs:comment "Champion class (Fighter, Mage, Tank, Assassin, Marksman, Support)."@en .
lol:ResourceType   a owl:Class ; rdfs:label "Resource Type"@en .
lol:Region         a owl:Class ; rdfs:label "Region"@en ;
    rdfs:comment "A lore region of Runeterra."@en .
lol:Position       a owl:Class ; rdfs:label "Position"@en ;
    rdfs:comment "Intended in-game lane position."@en .
lol:CCEffect       a owl:Class ; rdfs:label "CC Effect"@en ;
    rdfs:comment "A crowd control status effect."@en .
lol:Mechanic       a owl:Class ; rdfs:label "Mechanic"@en ;
    rdfs:comment "A gameplay mechanic (Dash, Shield, Heal, etc.)."@en .
lol:PlaystyleTag   a owl:Class ; rdfs:label "Playstyle Tag"@en ;
    rdfs:comment "NLP-inferred playstyle descriptor."@en .
lol:BaseStats      a owl:Class ; rdfs:label "Base Stats"@en .
lol:Ratings        a owl:Class ; rdfs:label "Champion Ratings"@en ;
    rdfs:comment "Official wiki damage/toughness/control/mobility ratings (1-3 scale)."@en .

# ══════════════════════════════════════════════════════════════
# OBJECT PROPERTIES
# ══════════════════════════════════════════════════════════════

lol:hasRole           a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Role .
lol:hasResourceType   a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:ResourceType .
lol:hasSpell          a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Spell .
lol:hasPassive        a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:PassiveAbility .
lol:hasSkin           a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Skin .
lol:hasStats          a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:BaseStats .
lol:hasRatings        a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Ratings .
lol:isFromRegion      a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Region ;
    rdfs:label "is from region"@en .
lol:playsPosition     a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Position ;
    rdfs:label "plays position"@en .
lol:hasPlaystyleTag   a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:PlaystyleTag .
lol:champHasCCEffect  a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:CCEffect .
lol:champHasMechanic  a owl:ObjectProperty ; rdfs:domain lol:Champion ; rdfs:range lol:Mechanic .
lol:hasCCEffect       a owl:ObjectProperty ; rdfs:domain lol:Spell    ; rdfs:range lol:CCEffect .
lol:hasMechanic       a owl:ObjectProperty ; rdfs:domain lol:Spell    ; rdfs:range lol:Mechanic .
lol:isAllyOf          a owl:ObjectProperty, owl:SymmetricProperty ;
    rdfs:domain lol:Champion ; rdfs:range lol:Champion ; rdfs:label "is ally of (lore)"@en .
lol:isEnemyOf         a owl:ObjectProperty, owl:SymmetricProperty ;
    rdfs:domain lol:Champion ; rdfs:range lol:Champion ; rdfs:label "is enemy of (lore)"@en .
lol:mentions          a owl:ObjectProperty ;
    rdfs:domain lol:Champion ; rdfs:range lol:Champion ; rdfs:label "mentions in lore"@en .
lol:belongsToChampion a owl:ObjectProperty ; owl:inverseOf lol:hasSpell ;
    rdfs:domain lol:Spell ; rdfs:range lol:Champion .

# ══════════════════════════════════════════════════════════════
# DATATYPE PROPERTIES
# ══════════════════════════════════════════════════════════════

lol:championId         a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:championKey        a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string ;
    rdfs:comment "Riot API numeric key."@en .
lol:championName       a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:championTitle      a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:lore               a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:blurb              a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:allyTip            a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:enemyTip           a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .
lol:adaptiveType       a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string ;
    rdfs:comment "Physical or Magic adaptive damage type."@en .
lol:costBE             a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:integer ;
    rdfs:comment "Blue Essence store cost."@en .
lol:costRP             a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:integer ;
    rdfs:comment "RP store cost."@en .
lol:lastChanged        a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string ;
    rdfs:comment "Patch when the champion was last updated."@en .
lol:dataVersion        a owl:DatatypeProperty ; rdfs:domain lol:Champion ; rdfs:range xsd:string .

# Stats
lol:hp                    a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:hpPerLevel            a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:mp                    a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:mpPerLevel            a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:movespeed             a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:armor                 a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:armorPerLevel         a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:spellblock            a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:spellblockPerLevel    a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:attackrange           a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:hpregen               a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:hpregenPerLevel       a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:mpregen               a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:mpregenPerLevel       a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:attackdamage          a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:attackdamagePerLevel  a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:attackspeed           a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:attackspeedPerLevel   a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .
lol:crit                  a owl:DatatypeProperty ; rdfs:domain lol:BaseStats ; rdfs:range xsd:double .

# Ratings (wiki 1-3 scale)
lol:ratingDamage      a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer ;
    rdfs:comment "Damage rating 1-3 (official wiki)."@en .
lol:ratingToughness   a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer .
lol:ratingControl     a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer .
lol:ratingMobility    a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer .
lol:ratingUtility     a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer .
lol:ratingDifficulty  a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer .
lol:ratingStyle       a owl:DatatypeProperty ; rdfs:domain lol:Ratings ; rdfs:range xsd:integer ;
    rdfs:comment "0=AA-focused, 100=ability-focused."@en .

# Spell
lol:spellId          a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .
lol:spellName        a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .
lol:spellDescription a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .
lol:spellTooltip     a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .
lol:spellSlot        a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:string .
lol:maxRank          a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:integer .
lol:cooldownBurn     a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:string .
lol:costBurn         a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:string .
lol:costType         a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:string .
lol:rangeBurn        a owl:DatatypeProperty ; rdfs:domain lol:ActiveSpell ; rdfs:range xsd:string .
lol:damageType       a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .
lol:targetType       a owl:DatatypeProperty ; rdfs:domain lol:Spell ; rdfs:range xsd:string .

# Skin
lol:skinId           a owl:DatatypeProperty ; rdfs:domain lol:Skin ; rdfs:range xsd:string .
lol:skinName         a owl:DatatypeProperty ; rdfs:domain lol:Skin ; rdfs:range xsd:string .
lol:skinNum          a owl:DatatypeProperty ; rdfs:domain lol:Skin ; rdfs:range xsd:integer .
lol:hasChromas       a owl:DatatypeProperty ; rdfs:domain lol:Skin ; rdfs:range xsd:boolean .

# Vocabulary labels
lol:roleName         a owl:DatatypeProperty ; rdfs:domain lol:Role         ; rdfs:range xsd:string .
lol:resourceName     a owl:DatatypeProperty ; rdfs:domain lol:ResourceType ; rdfs:range xsd:string .
lol:regionName       a owl:DatatypeProperty ; rdfs:domain lol:Region       ; rdfs:range xsd:string .
lol:positionName     a owl:DatatypeProperty ; rdfs:domain lol:Position     ; rdfs:range xsd:string .
lol:ccEffectName     a owl:DatatypeProperty ; rdfs:domain lol:CCEffect     ; rdfs:range xsd:string .
lol:mechanicName     a owl:DatatypeProperty ; rdfs:domain lol:Mechanic     ; rdfs:range xsd:string .
lol:playstyleTagName a owl:DatatypeProperty ; rdfs:domain lol:PlaystyleTag ; rdfs:range xsd:string .
'''


def vocab_individuals() -> str:
    lines = ["\n# ══════════════════════════════════════════════════════════════",
             "# VOCABULARY INDIVIDUALS",
             "# ══════════════════════════════════════════════════════════════\n"]

    for r in ROLES:
        lines.append(f'role:{r} a lol:Role, owl:NamedIndividual ; lol:roleName "{r}" .')
    lines.append("")
    for r in RESOURCES:
        label = r.replace("_"," ")
        lines.append(f'res:{r} a lol:ResourceType, owl:NamedIndividual ; lol:resourceName "{label}" .')
    lines.append("")
    for r in REGIONS:
        label = r.replace("_"," ")
        lines.append(f'region:{r} a lol:Region, owl:NamedIndividual ; lol:regionName "{label}" .')
    lines.append("")
    for p in POSITIONS:
        label = p.replace("_","/")
        lines.append(f'pos:{p} a lol:Position, owl:NamedIndividual ; lol:positionName "{label}" .')
    lines.append("")
    for c in CC_LIST:
        label = c.replace("_"," ")
        lines.append(f'cc:{c} a lol:CCEffect, owl:NamedIndividual ; lol:ccEffectName "{label}" .')
    lines.append("")
    for m in MECHANICS:
        label = m.replace("_"," ")
        lines.append(f'mech:{m} a lol:Mechanic, owl:NamedIndividual ; lol:mechanicName "{label}" .')
    lines.append("")
    for t in PLAYSTYLE:
        label = t.replace("_"," ")
        lines.append(f'style:{t} a lol:PlaystyleTag, owl:NamedIndividual ; lol:playstyleTagName "{label}" .')
    lines.append("")
    return "\n".join(lines)


def champion_to_ttl(c: dict) -> str:
    lines = []
    curi = safe_uri(c["name"])

    # ── Champion ──
    cl = [f"champ:{curi} a lol:Champion, owl:NamedIndividual ;"]
    cl.append(f"    lol:championId {esc(c.get('id',''))} ;")
    cl.append(f"    lol:championKey {esc(c.get('key',''))} ;")
    cl.append(f"    lol:championName {esc(c.get('name',''))} ;")
    cl.append(f"    lol:championTitle {esc(c.get('title',''))} ;")
    if c.get("blurb"):
        cl.append(f"    lol:blurb {esc(c['blurb'])} ;")
    if c.get("lore"):
        cl.append(f"    lol:lore {esc(c['lore'])} ;")
    if c.get("adaptivetype"):
        cl.append(f"    lol:adaptiveType {esc(c['adaptivetype'])} ;")
    if c.get("last_changed"):
        cl.append(f"    lol:lastChanged {esc(c['last_changed'])} ;")
    if c.get("cost_be"):
        cl.append(f"    lol:costBE {xsd_i(int(c['cost_be']))} ;")
    if c.get("cost_rp"):
        cl.append(f"    lol:costRP {xsd_i(int(c['cost_rp']))} ;")
    if c.get("version"):
        cl.append(f"    lol:dataVersion {esc(c['version'])} ;")
    for tip in c.get("allytips", []):
        cl.append(f"    lol:allyTip {esc(tip)} ;")
    for tip in c.get("enemytips", []):
        cl.append(f"    lol:enemyTip {esc(tip)} ;")

    # Roles
    for role in c.get("roles", []):
        if safe_uri(role) in [safe_uri(r) for r in ROLES]:
            cl.append(f"    lol:hasRole role:{safe_uri(role)} ;")

    # Resource
    resource = c.get("resource", "").strip()
    if resource:
        cl.append(f"    lol:hasResourceType res:{safe_uri(resource)} ;")

    # Regions
    for reg in c.get("regions", []):
        cl.append(f"    lol:isFromRegion region:{region_uri(reg)} ;")

    # Positions
    for p in c.get("positions", []):
        cl.append(f"    lol:playsPosition pos:{pos_uri(p)} ;")

    # CC & mechanics (champion level)
    for cc in c.get("champion_cc_effects", []):
        if cc in CC_LIST:
            cl.append(f"    lol:champHasCCEffect cc:{cc} ;")
    for m in c.get("champion_mechanics", []):
        if m in MECHANICS:
            cl.append(f"    lol:champHasMechanic mech:{m} ;")
    for t in c.get("playstyle_tags", []):
        if t in PLAYSTYLE:
            cl.append(f"    lol:hasPlaystyleTag style:{t} ;")

    # Relations lore
    rel = c.get("relations", {})
    for ally in rel.get("allies", []):
        cl.append(f"    lol:isAllyOf champ:{safe_uri(ally)} ;")
    for enemy in rel.get("enemies", []):
        cl.append(f"    lol:isEnemyOf champ:{safe_uri(enemy)} ;")
    for mention in rel.get("mentioned", []):
        cl.append(f"    lol:mentions champ:{safe_uri(mention)} ;")

    # Spells
    for i, ab in enumerate(c.get("abilities", [])):
        slot = ab.get("slot", f"S{i}")
        cl.append(f"    lol:hasSpell spell:{curi}_{safe_uri(slot)} ;")

    # Passive
    if c.get("passive", {}).get("name"):
        cl.append(f"    lol:hasPassive spell:{curi}_Passive ;")

    # Skins
    for skin in c.get("skins", []):
        cl.append(f"    lol:hasSkin skin:{safe_uri('skin_'+str(skin['id']))} ;")

    cl.append(f"    lol:hasStats champ:{curi}_stats ;")
    cl.append(f"    lol:hasRatings champ:{curi}_ratings .")

    lines.append("\n".join(cl))
    lines.append("")

    # ── Stats ──
    stats = c.get("stats", {})
    stat_map = [
        ("hp","hp"),("hpperlevel","hpPerLevel"),("mp","mp"),("mpperlevel","mpPerLevel"),
        ("movespeed","movespeed"),("armor","armor"),("armorperlevel","armorPerLevel"),
        ("spellblock","spellblock"),("spellblockperlevel","spellblockPerLevel"),
        ("attackrange","attackrange"),("hpregen","hpregen"),("hpregenperlevel","hpregenPerLevel"),
        ("mpregen","mpregen"),("mpregenperlevel","mpregenPerLevel"),
        ("attackdamage","attackdamage"),("attackdamageperlevel","attackdamagePerLevel"),
        ("attackspeed","attackspeed"),("attackspeedperlevel","attackspeedPerLevel"),
        ("crit","crit"),
    ]
    entries = [f"    lol:{prop} {xsd_d(stats[jk])}" for jk, prop in stat_map if jk in stats and stats[jk] is not None]
    if entries:
        lines.append(f"champ:{curi}_stats a lol:BaseStats, owl:NamedIndividual ;\n" + " ;\n".join(entries) + " .")
        lines.append("")

    # ── Ratings ──
    rat = c.get("ratings", {})
    rat_map = [("damage","ratingDamage"),("toughness","ratingToughness"),("control","ratingControl"),
               ("mobility","ratingMobility"),("utility","ratingUtility"),("difficulty","ratingDifficulty"),
               ("style","ratingStyle")]
    rentries = [f"    lol:{prop} {xsd_i(int(rat[k]))}" for k, prop in rat_map if k in rat and rat[k] is not None]
    if rentries:
        lines.append(f"champ:{curi}_ratings a lol:Ratings, owl:NamedIndividual ;\n" + " ;\n".join(rentries) + " .")
        lines.append("")

    # ── Spells ──
    for ab in c.get("abilities", []):
        slot = ab.get("slot", "Q")
        sid  = f"{curi}_{safe_uri(slot)}"
        sp   = [f"spell:{sid} a lol:ActiveSpell, owl:NamedIndividual ;"]
        sp.append(f"    lol:spellSlot {esc(slot)} ;")
        if ab.get("id"):       sp.append(f"    lol:spellId {esc(ab['id'])} ;")
        if ab.get("name"):     sp.append(f"    lol:spellName {esc(ab['name'])} ;")
        if ab.get("description"): sp.append(f"    lol:spellDescription {esc(ab['description'])} ;")
        if ab.get("tooltip"):  sp.append(f"    lol:spellTooltip {esc(ab['tooltip'])} ;")
        if ab.get("maxrank"):  sp.append(f"    lol:maxRank {xsd_i(ab['maxrank'])} ;")
        cd = ab.get("cooldown_burn") or ab.get("cooldownBurn") or ab.get("cooldown_str","")
        if cd:  sp.append(f"    lol:cooldownBurn {esc(cd)} ;")
        cb = ab.get("cost_burn") or ab.get("costBurn","0")
        if cb:  sp.append(f"    lol:costBurn {esc(cb)} ;")
        ct = ab.get("cost_type") or ab.get("costType","")
        if ct:  sp.append(f"    lol:costType {esc(ct)} ;")
        rb = ab.get("range_burn") or ab.get("rangeBurn","")
        if rb:  sp.append(f"    lol:rangeBurn {esc(rb)} ;")
        for cc in ab.get("cc_effects", []):
            if cc in CC_LIST: sp.append(f"    lol:hasCCEffect cc:{cc} ;")
        for m in ab.get("mechanics", []):
            if m in MECHANICS: sp.append(f"    lol:hasMechanic mech:{m} ;")
        for d in ab.get("damage_types", []):
            sp.append(f"    lol:damageType {esc(d)} ;")
        for t in ab.get("target_types", []):
            sp.append(f"    lol:targetType {esc(t)} ;")
        sp.append(f"    lol:belongsToChampion champ:{curi} .")
        lines.append("\n".join(sp))
        lines.append("")

    # ── Passive ──
    passive = c.get("passive", {})
    if passive and passive.get("name"):
        pp = [f"spell:{curi}_Passive a lol:PassiveAbility, owl:NamedIndividual ;"]
        pp.append(f"    lol:spellName {esc(passive.get('name',''))} ;")
        pp.append(f"    lol:spellDescription {esc(passive.get('description',''))} ;")
        pp.append(f"    lol:belongsToChampion champ:{curi} .")
        lines.append("\n".join(pp))
        lines.append("")

    # ── Skins ──
    for skin in c.get("skins", []):
        sk = safe_uri("skin_" + str(skin["id"]))
        lines.append(
            f"skin:{sk} a lol:Skin, owl:NamedIndividual ;\n"
            f"    lol:skinId {esc(skin['id'])} ;\n"
            f"    lol:skinName {esc(skin.get('name',''))} ;\n"
            f"    lol:skinNum {xsd_i(skin.get('num',0))} ;\n"
            f"    lol:hasChromas {xsd_b(skin.get('chromas',False))} ."
        )
        lines.append("")

    return "\n".join(lines)


def generate_ttl(data: list[dict], output_path: str):
    log.info(f"Generating TTL for {len(data)} champions...")
    parts = [ONTOLOGY_HEADER, vocab_individuals()]
    parts.append(f"\n# ══ CHAMPION INDIVIDUALS ({len(data)}) ══\n")

    for i, champ in enumerate(data):
        if i % 50 == 0:
            log.info(f"  TTL: {i+1}/{len(data)}")
        parts.append(champion_to_ttl(champ))

    content = "\n".join(parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    kb = len(content) // 1024
    log.info(f"✅ TTL saved to {output_path} ({kb} KB, ~{content.count(' a owl:NamedIndividual')} individuals)")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="LoL Knowledge Graph Merger v3")
    parser.add_argument("--wiki",     default="wiki_raw.json",     help="Sortie de wiki_api.py")
    parser.add_argument("--dd",       default="ddragon_raw.json",  help="Sortie de ddragon.py")
    parser.add_argument("--enriched", default="enriched.json",     help="JSON final enrichi")
    parser.add_argument("--ttl",      default="lol_ontology_v3.ttl")
    parser.add_argument("--ttl-only", action="store_true",         help="Régénère le TTL depuis enriched.json")
    parser.add_argument("--no-nlp",   action="store_true",         help="Skip NLP enrichment")
    args = parser.parse_args()

    if not args.ttl_only:
        # Charge les sources
        wiki_data = []
        if Path(args.wiki).exists() and Path(args.wiki).stat().st_size > 2:
            with open(args.wiki, encoding="utf-8") as f:
                wiki_data = json.load(f)
            log.info(f"Wiki data: {len(wiki_data)} champions")
        else:
            log.warning(f"Wiki data not found ({args.wiki}) — DDragon only")

        dd_data = []
        if Path(args.dd).exists():
            with open(args.dd, encoding="utf-8") as f:
                dd_data = json.load(f)
            log.info(f"DDragon data: {len(dd_data)} champions")
        else:
            log.warning(f"DDragon data not found ({args.dd}) — Wiki only")

        if not wiki_data and not dd_data:
            log.error("No data sources found. Run wiki_api.py and/or ddragon.py first.")
            return

        # Merge
        merged = merge(wiki_data, dd_data)

        # NLP enrichment
        if not args.no_nlp:
            try:
                from nlp_extractor import enrich_all, print_stats
                merged = enrich_all(merged)
                print_stats(merged)
            except ImportError:
                log.warning("nlp_extractor.py not found — skipping NLP")
        
        with open(args.enriched, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        log.info(f"✅ Enriched JSON → {args.enriched}")
    else:
        with open(args.enriched, encoding="utf-8") as f:
            merged = json.load(f)
        log.info(f"Loaded {len(merged)} champions from {args.enriched}")

    generate_ttl(merged, args.ttl)


if __name__ == "__main__":
    main()
