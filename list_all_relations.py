import re
from collections import Counter

def list_all_relations(file_path, output_file):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    preds = re.findall(r'<[^>]+> (<[^>]+>) (?:<[^>]+>|"[^"]+") \.', content)
    counts = Counter(preds)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("EXHAUSTIVE LIST OF RELATIONS IN KNOWLEDGE GRAPH\n")
        f.write("===============================================\n\n")
        for p, count in counts.most_common():
            f.write(f"{p} | Total Triples: {count}\n")
            
    print(f"Saved {len(counts)} unique relations to {output_file}")

if __name__ == "__main__":
    list_all_relations('data/processed/final_kb.nt', 'all_relations.txt')
