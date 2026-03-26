import rdflib
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PRIVATE_TTL = "lol_ontology_v3.ttl"
EXPANDED_NT = "data/processed/expanded_kb_2hop.nt"
FINAL_NT = "data/processed/final_kb.nt"

def load_private_kb(ttl_path):
    """Load the private KB using rdflib for robust parsing."""
    g = Graph()
    try:
        g.parse(ttl_path, format="turtle")
    except Exception as e:
        log.error(f"Error parsing {ttl_path}: {e}")
        return []
    
    triples = []
    for s, p, o in g:
        # We need to format them as NT-style strings for consistency with Wikidata data
        s_str = f"<{s}>"
        p_str = f"<{p}>"
        if isinstance(o, URIRef):
            o_str = f"<{o}>"
        elif isinstance(o, Literal):
            # Escape quotes and keep it simple
            val = str(o).replace('"', '\\"')
            o_str = f'"{val}"'
        else:
            # Skip BNodes or other types if not relevant for KGE
            continue
            
        triples.append(f"{s_str} {p_str} {o_str} .")
    return triples

def main():
    log.info("Cleaning and Merging final Knowledge Base...")
    
    # 1. Convert Private KB to NT
    private_triples = load_private_kb(PRIVATE_TTL)
    log.info(f"Loaded {len(private_triples)} private triples.")
    
    # 2. Load and Filter Expanded Triples
    with open(EXPANDED_NT, encoding="utf-8") as f:
        expanded_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    log.info(f"Loaded {len(expanded_lines)} raw expanded triples.")
    
    # Analyze relations in expanded KB to filter them
    from collections import Counter
    expanded_preds = []
    for t in expanded_lines:
        parts = t.split()
        if len(parts) >= 2:
            expanded_preds.append(parts[1])
    
    pred_counts = Counter(expanded_preds)
    # We take top 120 to stay safe within 200 total (Private 77 + ~120 = ~197)
    top_expanded_preds = [p for p, count in pred_counts.most_common(120)]
    
    filtered_expanded = [t for t in expanded_lines if t.split()[1] in top_expanded_preds]
    log.info(f"Filtered to top 120 Wikidata relations: {len(filtered_expanded)} triples remaining.")
    
    # 3. Merge and Unique
    all_triples = list(set(private_triples + filtered_expanded))
    log.info(f"Merged total: {len(all_triples)} unique triples.")
    
    # 4. Write Final NT
    with open(FINAL_NT, "w", encoding="utf-8") as f:
        for t in all_triples:
            f.write(t + "\n")
            
    # 5. Calculate Final Stats
    entities = set()
    relations = set()
    for t in all_triples:
        parts = t.split()
        if len(parts) >= 3:
            entities.add(parts[0])
            relations.add(parts[1])
            if parts[2].startswith("<"):
                entities.add(parts[2])
                
    log.info("=========================================")
    log.info("FINAL KB STATISTICS")
    log.info("=========================================")
    log.info(f"Total Triplets  : {len(all_triples)}")
    log.info(f"Total Entities  : {len(entities)}")
    log.info(f"Total Relations : {len(relations)}")
    log.info("=========================================")
    log.info(f"Final KB saved to: {FINAL_NT}")

if __name__ == "__main__":
    main()