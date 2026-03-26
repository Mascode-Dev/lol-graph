import re
from collections import Counter

def get_all_predicates(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to find all predicates in <subject> <predicate> <object> .
    preds = re.findall(r'<[^>]+> (<[^>]+>) (?:<[^>]+>|"[^"]+") \.', content)
    
    # Group by prefix to make it readable
    lol_preds = [p for p in set(preds) if "leagueoflegends" in p]
    wd_preds = [p for p in set(preds) if "wikidata" in p]
    other_preds = [p for p in set(preds) if p not in lol_preds and p not in wd_preds]
    
    print("--- LoL Ontology Predicates ---")
    for p in sorted(lol_preds):
        print(p)
        
    print("\n--- Wikidata Predicates (Top 50) ---")
    wd_counts = Counter([p for p in preds if "wikidata" in p])
    for p, count in wd_counts.most_common(50):
        print(f"{p} ({count} occurrences)")

if __name__ == "__main__":
    get_all_predicates('data/processed/final_kb.nt')
