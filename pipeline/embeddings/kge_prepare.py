from rdflib import Graph, URIRef
import random
import os

def clean_and_split(input_file, output_dir):
    triples = []
    entities = set()
    relations = set()

    print(f"Reading {input_file} manually for robustness...")
    # Manual parser
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # Simple heuristic for entity-entity triples
            parts = line.split()
            if len(parts) < 4: continue
            
            s = parts[0]
            p = parts[1]
            o = parts[2]
            
            # Check if they look like URIs or the 'a' shorthand
            if s.startswith('<') and s.endswith('>') and o.startswith('<') and o.endswith('>'):
                s_uri = s[1:-1]
                o_uri = o[1:-1]
                if p.startswith('<') and p.endswith('>'):
                    p_uri = p[1:-1]
                elif p == 'a':
                    p_uri = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
                else:
                    continue
                
                triples.append((s_uri, p_uri, o_uri))
                entities.add(s_uri)
                entities.add(o_uri)
                relations.add(p_uri)
    
    print(f"Loaded {len(triples)} entity-entity triples.")
    print(f"Unique entities: {len(entities)}")
    print(f"Unique relations: {len(relations)}")

    # Remove duplicates
    triples = list(set(triples))
    print(f"Triples after deduplication: {len(triples)}")

    # Shuffle
    random.seed(42)
    random.shuffle(triples)

    # Initial split (80/10/10)
    n = len(triples)
    train_size = int(0.8 * n)
    valid_size = int(0.1 * n)
    
    train_triples = triples[:train_size]
    valid_triples_raw = triples[train_size:train_size + valid_size]
    test_triples_raw = triples[train_size + valid_size:]

    # Ensure no entity appears only in validation/test
    train_entities = set()
    for s, p, o in train_triples:
        train_entities.add(s)
        train_entities.add(o)

    final_valid_triples = []
    final_test_triples = []

    for s, p, o in valid_triples_raw:
        if s in train_entities and o in train_entities:
            final_valid_triples.append((s, p, o))
        else:
            train_triples.append((s, p, o))
            train_entities.add(s)
            train_entities.add(o)

    for s, p, o in test_triples_raw:
        if s in train_entities and o in train_entities:
            final_test_triples.append((s, p, o))
        else:
            train_triples.append((s, p, o))
            train_entities.add(s)
            train_entities.add(o)

    print(f"Final counts:")
    print(f"Train: {len(train_triples)}")
    print(f"Valid: {len(final_valid_triples)}")
    print(f"Test:  {len(final_test_triples)}")

    # Save to files
    os.makedirs(output_dir, exist_ok=True)
    
    def save_triples(trips, filename):
        path = os.path.join(output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            for s, p, o in trips:
                f.write(f"{s}\t{p}\t{o}\n")
        print(f"Saved {filename}")

    save_triples(train_triples, 'train.txt')
    save_triples(final_valid_triples, 'valid.txt')
    save_triples(final_test_triples, 'test.txt')

if __name__ == "__main__":
    input_kb = "data/processed/final_kb.nt"
    output_folder = "data/kge"
    clean_and_split(input_kb, output_folder)
