import os
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

PRIVATE_TTL = "lol_ontology_v3.ttl"
EXPANDED_NT = "data/processed/expanded_kb_2hop.nt"
FINAL_NT = "data/processed/final_kb.nt"

def ttl_to_nt_simple(ttl_path):
    """Very basic conversion of our specific TTL to NT by stripping prefixes and comments."""
    # Note: In a production environment, use rdflib. 
    # Here we do it manually to avoid dependency issues and stay fast.
    triples = []
    prefixes = {
        "lol:": "<http://leagueoflegends.knowledge/ontology#",
        "champ:": "<http://leagueoflegends.knowledge/champion/",
        "spell:": "<http://leagueoflegends.knowledge/spell/",
        "region:": "<http://leagueoflegends.knowledge/region/",
        "pos:": "<http://leagueoflegends.knowledge/position/",
        "role:": "<http://leagueoflegends.knowledge/role/",
        "cc:": "<http://leagueoflegends.knowledge/cc_effect/",
        "mech:": "<http://leagueoflegends.knowledge/mechanic/",
        "style:": "<http://leagueoflegends.knowledge/playstyle/",
        "rdfs:": "<http://www.w3.org/2000/01/rdf-schema#",
        "rdf:": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "owl:": "<http://www.w3.org/2002/07/owl#",
        "xsd:": "<http://www.w3.org/2001/XMLSchema#",
    }
    
    with open(ttl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("@") or line.startswith("#"):
                continue
            
            # Simple triplet line: s p o ; or s p o .
            # This is a simplification for our specific file structure
            parts = line.split()
            if len(parts) >= 3:
                s, p, o = parts[0], parts[1], parts[2]
                
                # Replace prefixes
                for pref, uri in prefixes.items():
                    if s.startswith(pref): s = s.replace(pref, uri).replace(";", "") + ">"
                    if p.startswith(pref): p = p.replace(pref, uri).replace(";", "") + ">"
                    if o.startswith(pref): o = o.replace(pref, uri).replace(";", "") + ">"
                
                # Basic literal check
                if not o.startswith("<") and not o.startswith("\""):
                    o = f"\"{o}\""
                
                triples.append(f"{s} {p} {o} .")
    return triples

def main():
    log.info("Cleaning and Merging final Knowledge Base...")
    
    # 1. Convert Private KB to NT
    private_triples = ttl_to_nt_simple(PRIVATE_TTL)
    log.info(f"Loaded {len(private_triples)} private triples.")
    
    # 2. Load Expanded Triples
    with open(EXPANDED_NT, encoding="utf-8") as f:
        expanded_triples = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    log.info(f"Loaded {len(expanded_triples)} expanded triples.")
    
    # 3. Merge and Unique
    all_triples = list(set(private_triples + expanded_triples))
    log.info(f"Merged total: {len(all_triples)} unique triples.")
    
    # 4. Write Final NT
    with open(FINAL_NT, "w", encoding="utf-8") as f:
        for t in all_triples:
            f.write(t + "\n")
            
    # 5. Calculate Final Stats (Step 4 Requirement)
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
    log.info("📊 FINAL KB STATISTICS (LAB 4)")
    log.info("=========================================")
    log.info(f"Total Triplets  : {len(all_triples)}")
    log.info(f"Total Entities  : {len(entities)}")
    log.info(f"Total Relations : {len(relations)}")
    log.info("=========================================")
    log.info(f"✅ Final KB saved to: {FINAL_NT}")

if __name__ == "__main__":
    main()