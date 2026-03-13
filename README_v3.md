# LoL Knowledge Graph v3 — Pipeline Complet

## Architecture

```
wiki.leagueoflegends.com          ddragon.leagueoflegends.com
        │                                    │
   wiki_api.py                          ddragon.py
        │                                    │
   data/raw/wiki_raw.json         data/raw/ddragon_raw.json
        └──────────────┬─────────────────────┘
                    merge.py
                 (+ nlp_extractor.py)
                       │
            data/processed/enriched.json
                       │
               lol_ontology_v3.ttl
                       │
                   Protégé / HermiT
```

### Rôle de chaque script

| Script | Source | Ce qu'il apporte |
|--------|--------|-----------------|
| `wiki_api.py` | wiki.leagueoflegends.com (officiel) | Roles, positions **officielles**, ratings damage/toughness/control/mobility/utility (1-3), style, adaptivetype, lore, régions, spell names, BE/RP cost, last_changed |
| `ddragon.py` | ddragon.leagueoflegends.com (officiel) | Stats précises, **sorts complets** (cooldown/coût/range par rank + tooltip), passive, skins, lore, blurb, ally/enemy tips |
| `nlp_extractor.py` | Textes des sorts | CC effects (17 types), damage types, target types, mécaniques (20 types), playstyle tags inférés |
| `merge.py` | Tous les JSON | Fusion + génération TTL finale pour Protégé |

---

## 1. Installation

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

pip install requests beautifulsoup4 spacy
python -m spacy download en_core_web_sm
```

---

## 2. Workflow

### Option A — Pipeline complet (recommandé)

```bash
# Étape 1 — Wiki officiel (module Lua = 1 appel API pour 172 champions!)
# --module-only = ultra rapide (pas de fetch des pages HTML individuelles)
# Sans --module-only = fetch aussi le lore + abilities depuis les pages (plus lent mais plus riche)
python wiki_api.py --output data/raw/wiki_raw.json

# Option rapide (module Lua uniquement, ~5 secondes)
python wiki_api.py --module-only --output data/raw/wiki_raw.json

# Option complète (module + pages HTML, ~4 min)
python wiki_api.py --output data/raw/wiki_raw.json

# Étape 2 — Data Dragon (parallèle, ~2 min pour 172 champions)
python ddragon.py --output data/raw/ddragon_raw.json --stats

# Étape 3 — Merge + NLP + génération TTL
python merge.py \
  --wiki data/raw/wiki_raw.json \
  --dd   data/raw/ddragon_raw.json \
  --enriched data/processed/enriched.json \
  --ttl  lol_ontology_v3.ttl
```

### Option B — DDragon uniquement (si le wiki est inaccessible)

```bash
python ddragon.py --output data/raw/ddragon_raw.json
python merge.py --dd data/raw/ddragon_raw.json --wiki /dev/null \
  --enriched data/processed/enriched.json --ttl lol_ontology_v3.ttl
```

### Option C — Test sur 5 champions

```bash
python wiki_api.py --limit 5 --output data/raw/wiki_test.json
python ddragon.py  --limit 5 --output data/raw/dd_test.json
python merge.py --wiki data/raw/wiki_test.json --dd data/raw/dd_test.json \
  --enriched data/processed/test_enriched.json --ttl test.ttl
```

### Reprendre après interruption

```bash
# wiki_api.py sauvegarde tous les 15 champions
python wiki_api.py --resume data/raw/wiki_raw.json --output data/raw/wiki_raw.json
```

---

## 3. Données extraites par champion

```json
{
  "name": "Aatrox",
  "id": "Aatrox",
  "key": "266",
  "title": "the Darkin Blade",

  "roles": ["Fighter"],
  "positions": ["Top"],
  "resource": "Blood Well",
  "adaptivetype": "Physical",

  "ratings": {
    "damage": 2,
    "toughness": 2,
    "control": 1,
    "mobility": 2,
    "utility": 1,
    "difficulty": 2,
    "style": 15,
    "riot_attack": 8,
    "riot_defense": 4
  },

  "stats": {
    "hp": 650, "hpperlevel": 114,
    "armor": 38, "armorperlevel": 4.8,
    "movespeed": 345, "attackrange": 175,
    ...
  },

  "abilities": [
    {
      "slot": "Q",
      "id": "AatroxQ",
      "name": "The Darkin Blade",
      "description": "Aatrox slams his greatsword...",
      "tooltip": "...",
      "maxrank": 5,
      "cooldown": [14, 12, 10, 8, 6],
      "cooldown_burn": "14/12/10/8/6",
      "cost": [0, 0, 0, 0, 0],
      "cost_type": "No Cost",
      "range_burn": "25000",
      "cc_effects": ["Knock_Up"],
      "damage_types": ["Physical"],
      "target_types": ["AOE"],
      "mechanics": ["Recast"]
    }
  ],

  "passive": {
    "name": "Deathbringer Stance",
    "description": "Periodically, Aatrox's next basic attack..."
  },

  "skins": [
    {"id": "266001", "name": "Justicar Aatrox", "num": 1, "chromas": false}
  ],

  "lore": "Once honored defenders of Shurima...",
  "blurb": "...",
  "allytips": ["Use Umbral Dash while casting..."],
  "enemytips": ["Aatrox's attacks are very telegraphed..."],

  "regions": ["Shurima"],
  "last_changed": "V14.20",
  "cost_be": 3150,
  "cost_rp": 790,

  "champion_cc_effects": ["Knock_Up", "Pull", "Fear"],
  "champion_mechanics": ["Dash", "Heal", "Recast"],
  "playstyle_tags": ["High_Mobility", "Self_Sustain", "Hard_CC"],

  "relations": {
    "allies": [],
    "enemies": ["Tryndamere"],
    "mentioned": ["Riven", "Varus"],
    "lore_snippet": "Once honored defenders of Shurima..."
  }
}
```

---

## 4. Nouvelles classes dans l'ontologie v3

| Classe | Description |
|--------|-------------|
| `lol:Ratings` | Ratings officiels wiki 1-3 (damage/toughness/control/mobility/utility/difficulty/style) |
| `lol:Region` | Régions lore de Runeterra (15 régions) |
| `lol:Position` | Positions de jeu (Top/Jungle/Mid/Bot_ADC/Support) |
| `lol:CCEffect` | 17 effets CC (Stun, Root, Slow, Knock_Up, Fear, etc.) |
| `lol:Mechanic` | 20 mécaniques (Dash, Shield, Heal, Execute, Reset, etc.) |
| `lol:PlaystyleTag` | 18 tags inférés (High_Mobility, Hard_CC, AOE_Focus, etc.) |

### Nouvelles propriétés notables

- `lol:ratingDamage/Toughness/Control/Mobility/Utility/Style` — wiki 1-3 scale
- `lol:adaptiveType` — Physical ou Magic
- `lol:lastChanged` — patch dernière mise à jour
- `lol:costBE` / `lol:costRP` — prix en magasin
- `lol:isAllyOf` / `lol:isEnemyOf` — **SymmetricProperty** (inférence HermiT)
- `lol:hasCCEffect` au niveau sort ET `lol:champHasCCEffect` au niveau champion

---

## 5. SPARQL queries dans Protégé

```sparql
PREFIX lol:    <http://leagueoflegends.knowledge/ontology#>
PREFIX champ:  <http://leagueoflegends.knowledge/champion/>
PREFIX region: <http://leagueoflegends.knowledge/region/>
PREFIX cc:     <http://leagueoflegends.knowledge/cc_effect/>
PREFIX mech:   <http://leagueoflegends.knowledge/mechanic/>
PREFIX style:  <http://leagueoflegends.knowledge/playstyle/>
PREFIX pos:    <http://leagueoflegends.knowledge/position/>

# Champions de Noxus
SELECT ?name WHERE {
  ?c lol:isFromRegion region:Noxus ; lol:championName ?name .
}

# Champions avec Stun ET Dash ET qui jouent Top
SELECT ?name WHERE {
  ?c lol:champHasCCEffect cc:Stun ;
     lol:champHasMechanic mech:Dash ;
     lol:playsPosition pos:Top ;
     lol:championName ?name .
}

# Rating mobilité = 3 (maximum)
SELECT ?name ?mob WHERE {
  ?c lol:championName ?name ;
     lol:hasRatings ?r .
  ?r lol:ratingMobility ?mob .
  FILTER(?mob = 3)
}

# Champions avec Execute ET playstyle Hard_CC
SELECT ?name WHERE {
  ?c lol:champHasMechanic mech:Execute ;
     lol:hasPlaystyleTag style:Hard_CC ;
     lol:championName ?name .
}

# Top 10 HP de base
SELECT ?name ?hp WHERE {
  ?c lol:championName ?name ;
     lol:hasStats ?s .
  ?s lol:hp ?hp .
} ORDER BY DESC(?hp) LIMIT 10

# Tous les alliés de Lux (après inférence HermiT sur isAllyOf SymmetricProperty)
SELECT ?ally_name WHERE {
  champ:Lux lol:isAllyOf ?ally .
  ?ally lol:championName ?ally_name .
}
```

---

## 6. Importer dans Protégé

1. `File → Open` → `lol_ontology_v3.ttl` (format **Turtle**)
2. `Reasoner` → **HermiT 1.4** → `Start Reasoner`
3. Vérifier les inférences : `isAllyOf` (SymmetricProperty) → si A allié de B, B allié de A
4. Onglet `SPARQL Query` pour tester les requêtes ci-dessus
