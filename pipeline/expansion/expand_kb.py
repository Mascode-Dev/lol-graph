import csv
import requests
import time
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MAPPING_CSV_PATH = "data/processed/alignment_mapping.csv"
OUTPUT_NT_PATH = "data/processed/expanded_kb.nt"
CONFIDENCE_THRESHOLD = 0.7

def fetch_triplets(wd_uri):
    """Fetches 1-hop triplets for a given Wikidata URI."""
    # Use the QID from the full URI
    qid = wd_uri.split('/')[-1]
    
    url = "https://query.wikidata.org/sparql"
    # Query for outgoing and incoming properties
    # We filter out very long literals or deep metadata to keep the KB manageable
    query = f"""
    SELECT ?s ?p ?o WHERE {{
      {{ BIND(wd:{qid} AS ?s) . wd:{qid} ?p ?o . FILTER(!isLiteral(?o) || lang(?o) = "en" || lang(?o) = "") }}
      UNION
      {{ BIND(wd:{qid} AS ?o) . ?s ?p wd:{qid} . }}
    }} LIMIT 500
    """
    
    headers = {
        "Accept": "text/plain", # Requesting N-Triples/NT format directly if possible, or TSV
        "User-Agent": "LoL-KB-Expansion/1.0 (Python)"
    }
    
    try:
        response = requests.get(url, params={'query': query, 'format': 'json'}, headers=headers)
        if response.status_code == 429:
            log.warning("Rate limited. Sleeping...")
            time.sleep(5)
            return fetch_triplets(wd_uri)
            
        data = response.json()
        triples = []
        for result in data['results']['bindings']:
            s = result['s']['value']
            p = result['p']['value']
            o = result['o']['value']
            
            # Basic NT formatting
            s_str = f"<{s}>"
            p_str = f"<{p}>"
            if result['o']['type'] == 'uri':
                o_str = f"<{o}>"
            else:
                # Escape quotes in literals
                val = o.replace('"', '\\"')
                o_str = f'"{val}"'
                
            triples.append(f"{s_str} {p_str} {o_str} .")
        return triples
    except Exception as e:
        log.error(f"Error fetching {qid}: {e}")
        return []

def main():
    if not Path(MAPPING_CSV_PATH).exists():
        log.error("Mapping file not found.")
        return

    entities = []
    with open(MAPPING_CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if float(row['Confidence']) >= CONFIDENCE_THRESHOLD:
                entities.append(row['External URI'])

    log.info(f"Starting expansion for {len(entities)} entities...")
    
    all_new_triples = []
    for i, uri in enumerate(entities):
        if i % 10 == 0:
            log.info(f"Processing {i}/{len(entities)}...")
        
        triples = fetch_triplets(uri)
        all_new_triples.extend(triples)
        time.sleep(0.5) # Avoid aggressive rate limiting

    # Write to NT file
    with open(OUTPUT_NT_PATH, "w", encoding="utf-8") as f:
        # 1. Add comment header
        f.write(f"# Expanded KB - Generated on {time.ctime()}\n")
        f.write(f"# Source: Wikidata 1-Hop Expansion\n")
        
        # 2. Write new triples
        for t in all_new_triples:
            f.write(t + "\n")

    log.info(f"✅ Expansion complete! Added {len(all_new_triples)} new triples.")
    log.info(f"Saved to {OUTPUT_NT_PATH}")

if __name__ == "__main__":
    main()