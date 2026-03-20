import csv
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

MAPPING_CSV_PATH = "data/processed/alignment_mapping.csv"
PREDICATE_TTL_PATH = "data/processed/predicate_alignment.ttl"
CONFIDENCE_THRESHOLD = 0.7

def main():
    if not Path(MAPPING_CSV_PATH).exists():
        log.error(f"Mapping file not found: {MAPPING_CSV_PATH}. Please run Step 1 first.")
        return

    # 1. Define Predicate Alignments (as per Step 2/3 of Lab)
    # These are the "Ontological definition of newly created entities" mentioned in the PDF.
    predicates = [
        ("lol:championName", "rdfs:label", "Exact"),
        ("lol:lore", "schema:description", "Similar"),
        ("lol:isFromRegion", "wdt:P1080", "similar (from narrative universe)"),
        ("lol:playsPosition", "wdt:P413", "similar (position played)"),
        ("lol:hasStats", "wdt:P3373", "similar (related statistics)")
    ]

    # 2. Filter entities by confidence (Step 2 requirement)
    valid_entities = []
    with open(MAPPING_CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if float(row['Confidence']) >= CONFIDENCE_THRESHOLD:
                valid_entities.append(row)

    log.info(f"Filtering complete: {len(valid_entities)} entities meet the {CONFIDENCE_THRESHOLD} threshold.")

    # 3. Write Predicate Alignment TTL
    with open(PREDICATE_TTL_PATH, "w", encoding="utf-8") as f:
        f.write("@prefix owl: <http://www.w3.org/2002/07/owl#> .\n")
        f.write("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        f.write("@prefix wdt: <http://www.wikidata.org/prop/direct/> .\n")
        f.write("@prefix schema: <http://schema.org/> .\n")
        f.write("@prefix lol: <http://leagueoflegends.knowledge/ontology#> .\n\n")

        f.write("# --- Predicate Alignment (Step 2) ---\n")
        for priv, ext, note in predicates:
            f.write(f"{priv} owl:equivalentProperty <{ext}> . # {note}\n")
            
        f.write("\n# --- Filtered Entity Links (Confidence >= 0.7) ---\n")
        for entity in valid_entities:
            f.write(f"<{entity['Private Entity']}> owl:sameAs <{entity['External URI']}> .\n")

    log.info(f"✅ Predicate alignment and filtered links saved to {PREDICATE_TTL_PATH}")

if __name__ == "__main__":
    main()