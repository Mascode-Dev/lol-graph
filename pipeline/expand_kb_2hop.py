import csv
import requests
import time
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

INPUT_NT_PATH = "data/processed/expanded_kb.nt"
OUTPUT_NT_PATH = "data/processed/expanded_kb_2hop.nt"
MAX_ENTITIES = 500
TRIPLES_PER_ENTITY = 3000

def fetch_triplets(qid):
    """Fetches triplets for a given Wikidata QID."""
    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?p ?o WHERE {{
      wd:{qid} ?p ?o . 
      FILTER(!isLiteral(?o) || lang(?o) = "en" || lang(?o) = "")
    }} LIMIT {TRIPLES_PER_ENTITY}
    """
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "LoL-KB-Expansion/1.0 (Python)"
    }
    
    try:
        response = requests.get(url, params={'query': query, 'format': 'json'}, headers=headers)
        if response.status_code == 429:
            log.warning("Rate limited. Sleeping...")
            time.sleep(10)
            return fetch_triplets(qid)
            
        data = response.json()
        triples = []
        for result in data['results']['bindings']:
            p = result['p']['value']
            o = result['o']['value']
            
            s_str = f"<http://www.wikidata.org/entity/{qid}>"
            p_str = f"<{p}>"
            if result['o']['type'] == 'uri':
                o_str = f"<{o}>"
            else:
                val = o.replace('"', '\\"')
                o_str = f'"{val}"'
                
            triples.append(f"{s_str} {p_str} {o_str} .")
        return triples
    except Exception as e:
        log.error(f"Error fetching {qid}: {e}")
        return []

def main():
    if not Path(INPUT_NT_PATH).exists():
        log.error("1-hop NT file not found.")
        return

    # Extract all unique QIDs from the 1st hop
    with open(INPUT_NT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    qids = sorted(list(set(re.findall(r'http://www.wikidata.org/entity/(Q\d+)', content))))
    
    log.info(f"Found {len(qids)} unique Wikidata entities in 1-hop expansion.")
    
    # We prioritize the most frequent ones or simply take a representative sample
    to_expand = qids[:MAX_ENTITIES]
    log.info(f"Expanding top {len(to_expand)} entities for 2nd hop...")
    
    all_new_triples = []
    for i, qid in enumerate(to_expand):
        if i % 20 == 0:
            log.info(f"Processing {i}/{len(to_expand)}...")
        
        triples = fetch_triplets(qid)
        all_new_triples.extend(triples)
        time.sleep(0.3) # Avoid aggressive rate limiting

    # Write to NEW NT file (concatenating with 1st hop)
    with open(OUTPUT_NT_PATH, "w", encoding="utf-8") as f:
        # 1. Copy original 1-hop triples
        f.write(content)
        f.write(f"\n# --- 2-Hop Expansion Triples ---\n")
        
        # 2. Add new 2-hop triples
        for t in all_new_triples:
            f.write(t + "\n")

    log.info(f"✅ 2-Hop Expansion complete! Added {len(all_new_triples)} new triples.")
    log.info(f"Total expanded triples in file: {len(all_new_triples) + content.count('.')}")
    log.info(f"Saved to {OUTPUT_NT_PATH}")

if __name__ == "__main__":
    main()