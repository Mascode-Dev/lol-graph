import json
import requests
import time
import csv
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

ENRICHED_PATH = "data/processed/enriched.json"
MAPPING_CSV_PATH = "data/processed/alignment_mapping.csv"
ALIGNMENT_TTL_PATH = "data/processed/alignment.ttl"

def get_wikidata_bulk_lol_characters():
    """Fetches all entities linked to League of Legends from Wikidata via SPARQL."""
    log.info("Fetching known League of Legends characters from Wikidata via SPARQL...")
    url = "https://query.wikidata.org/sparql"
    # P1441 = present in work, P1080 = from narrative universe, Q1048473 = League of Legends
    query = """
    SELECT ?item ?itemLabel WHERE {
      { ?item wdt:P1441 wd:Q1048473. }
      UNION
      { ?item wdt:P1080 wd:Q1048473. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "LoL-KB-Expansion/1.0 (Python)"
    }
    try:
        response = requests.get(url, params={'query': query}, headers=headers)
        data = response.json()
        
        char_map = {}
        for result in data['results']['bindings']:
            uri = result['item']['value']
            name = result['itemLabel']['value']
            char_map[name.lower()] = uri
        
        log.info(f"Found {len(char_map)} LoL characters in Wikidata SPARQL.")
        return char_map
    except Exception as e:
        log.error(f"SPARQL query failed: {e}")
        return {}

def search_wikidata_api(name):
    """Fallback: Searches Wikidata API for a specific champion name."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "limit": 5
    }
    headers = {"User-Agent": "LoL-KB-Expansion/1.0 (Python)"}
    try:
        resp = requests.get(url, params=params, headers=headers)
        data = resp.json()
        
        for item in data.get('search', []):
            desc = item.get('description', '').lower()
            if 'league of legends' in desc:
                return "http://www.wikidata.org/entity/" + item['id'], 0.95
            elif 'video game character' in desc or 'fictional character' in desc:
                return "http://www.wikidata.org/entity/" + item['id'], 0.80
                
        if data.get('search'):
            return "http://www.wikidata.org/entity/" + data['search'][0]['id'], 0.50
            
    except Exception as e:
        pass
    return None, 0.0

def main():
    if not Path(ENRICHED_PATH).exists():
        log.error(f"File not found: {ENRICHED_PATH}")
        return

    with open(ENRICHED_PATH, encoding="utf-8") as f:
        champions = json.load(f)

    bulk_map = get_wikidata_bulk_lol_characters()
    
    alignments = []
    
    log.info(f"Aligning {len(champions)} champions...")
    
    for champ in champions:
        name = champ['name']
        safe_name = name.replace(" ", "_").replace("'", "")
        private_uri = f"http://leagueoflegends.knowledge/champion/{safe_name}"
        
        # 1. Try exact match from SPARQL bulk map
        if name.lower() in bulk_map:
            wd_uri = bulk_map[name.lower()]
            alignments.append((private_uri, wd_uri, 0.99, name))
            continue
            
        # 2. Try partial match (e.g. Nunu & Willump -> Nunu)
        found_in_bulk = False
        for wd_name, wd_uri in bulk_map.items():
            if name.lower() in wd_name or wd_name in name.lower():
                alignments.append((private_uri, wd_uri, 0.90, name))
                found_in_bulk = True
                break
        
        if found_in_bulk:
            continue
            
        # 3. Fallback to API search
        time.sleep(0.1) # Be polite to API
        wd_uri, confidence = search_wikidata_api(name)
        if wd_uri:
            alignments.append((private_uri, wd_uri, confidence, name))
        else:
            log.warning(f"Could not find Wikidata entity for: {name}")
            # As per lab: "If it does not exist -> create a new entity". 
            # We don't have write access to Wikidata, so we just log 0 confidence.
            alignments.append((private_uri, "NOT_FOUND", 0.0, name))

    # Write MAPPING TABLE (CSV)
    with open(MAPPING_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Private Entity", "External URI", "Confidence", "Label"])
        for priv, ext, conf, label in alignments:
            writer.writerow([priv, ext, conf, label])
            
    log.info(f"✅ Mapping table saved to {MAPPING_CSV_PATH}")

    # Write ALIGNMENT TTL
    with open(ALIGNMENT_TTL_PATH, "w", encoding="utf-8") as f:
        f.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
        f.write("@prefix champ: <http://leagueoflegends.knowledge/champion/> .\n\n")
        
        linked_count = 0
        for priv, ext, conf, label in alignments:
            if conf > 0.0 and ext != "NOT_FOUND":
                f.write(f"<{priv}> owl:sameAs <{ext}> .\n")
                linked_count += 1
                
    log.info(f"✅ Alignment TTL saved to {ALIGNMENT_TTL_PATH} ({linked_count} links)")
    
    # Check stats
    high_conf = sum(1 for _, _, c, _ in alignments if c >= 0.90)
    log.info(f"Alignment successful for {linked_count}/{len(champions)} champions ({high_conf} with High Confidence).")

if __name__ == "__main__":
    main()