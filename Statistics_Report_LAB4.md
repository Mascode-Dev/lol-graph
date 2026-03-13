# Statistics Report - Lab 4: Knowledge Base Expansion
**Project:** LoL Knowledge Graph
**Date:** 2026-03-13

## 1. Volume Statistics
As required by the lab documentation, the following metrics describe the final state of the expanded Knowledge Base after alignment with Wikidata.

| Component | Count |
|-----------|-------|
| **Number of Triplets** | 48,062 |
| **Number of Entities** | 23,911 |
| **Number of Relations** | 12,283 |

## 2. Expansion Details
- **Base KB:** 31,290 triplets (LoL private data).
- **Expansion Method:** Anchored SPARQL expansion (Wikidata).
- **Expansion Depth:** 2-Hops (Champions -> Linked Entities -> Their attributes).
- **Confidence Threshold:** $\ge 0.70$ for all aligned entities.

## 3. Connectivity Analysis
- **Average Degree:** ~2.01 triplets per entity.
- **Components:** The graph is centered around 170 core "Anchor Entities" (LoL Champions) which are successfully linked to the global LOD cloud via `owl:sameAs`.
- **Format:** The final KB is exported in N-Triples (`.nt`) format for compatibility with Knowledge Graph Embedding (KGE) libraries.
