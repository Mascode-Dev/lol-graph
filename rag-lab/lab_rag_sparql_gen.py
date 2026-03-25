import re
import requests
import json
from typing import List, Tuple
from rdflib import Graph

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
# Remplacez par le chemin vers votre graphe final contenant les données.
# Par exemple : "../lol_ontology_v3.ttl" ou "../data/processed/final_kb.nt"
KG_FILE = "../lol_ontology_v3.ttl" 
OLLAMA_URL = "http://localhost:11434/api/generate"
# Vous pouvez changer pour "llama3", "deepseek-r1", "qwen", etc. selon ce que vous avez téléchargé
LLM_MODEL = "llama3.1:8b" 

MAX_PREDICATES = 80
MAX_CLASSES = 40
SAMPLE_TRIPLES = 20

# ---------------------------------------------------------
# 0) Utility: Call local LLM (Ollama)
# ---------------------------------------------------------
def ask_local_llm(prompt: str, model: str = LLM_MODEL) -> str:
    """Send a prompt to local Ollama model using REST API."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")
        
        data = response.json()
        return data.get("response", "")
    except requests.exceptions.ConnectionError:
        print(f"\n[ERREUR] Impossible de se connecter à Ollama sur {OLLAMA_URL}.")
        print("Vérifiez que l'application Ollama est bien lancée et tourne en arrière-plan.")
        return ""

# ---------------------------------------------------------
# 1) Load RDF Graph
# ---------------------------------------------------------
def load_graph(file_path: str) -> Graph:
    g = Graph()
    print(f"Loading graph from {file_path} (This might take a moment)...")
    # Guess format based on extension
    fmt = "turtle" if file_path.endswith(".ttl") else "nt" if file_path.endswith(".nt") else "xml"
    g.parse(file_path, format=fmt)
    print(f"Loaded {len(g)} triples from {file_path}")
    return g

# ---------------------------------------------------------
# 2) Build Schema Summary
# ---------------------------------------------------------
def get_prefix_block(g: Graph) -> str:
    defaults = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "lol": "http://leagueoflegends.knowledge/ontology#" # Préfixe personnalisé LoL
    }
    ns_map = {p: str(ns) for p, ns in g.namespace_manager.namespaces()}
    for k, v in defaults.items():
        ns_map.setdefault(k, v)
    
    lines = [f"PREFIX {p}: <{ns}>" for p, ns in ns_map.items()]
    return "\n".join(sorted(lines))

def list_distinct_predicates(g: Graph, limit=MAX_PREDICATES) -> List[str]:
    q = f"""
    SELECT DISTINCT ?p WHERE {{
      ?s ?p ?o .
    }} LIMIT {limit}
    """
    return [str(row.p) for row in g.query(q)]

def list_distinct_classes(g: Graph, limit=MAX_CLASSES) -> List[str]:
    q = f"""
    SELECT DISTINCT ?cls WHERE {{
      ?s a ?cls .
    }} LIMIT {limit}
    """
    return [str(row.cls) for row in g.query(q)]

def sample_triples(g: Graph, limit=SAMPLE_TRIPLES) -> List[Tuple[str, str, str]]:
    q = f"""
    SELECT ?s ?p ?o WHERE {{
      ?s ?p ?o .
      FILTER(isIRI(?s) && isIRI(?p) && isLiteral(?o)) # Préfère les littéraux pour montrer des exemples de textes
    }} LIMIT {limit}
    """
    return [(str(r.s), str(r.p), str(r.o)) for r in g.query(q)]

def build_schema_summary(g: Graph) -> str:
    prefixes = get_prefix_block(g)
    preds = list_distinct_predicates(g)
    clss = list_distinct_classes(g)
    samples = sample_triples(g)
    
    pred_lines = "\n".join(f"- {p}" for p in preds)
    cls_lines = "\n".join(f"- {c}" for c in clss)
    sample_lines = "\n".join(f"- {s} {p} \"{o}\"" for s, p, o in samples)
    
    summary = f"""
{prefixes}

# Predicates (sampled, unique up to {MAX_PREDICATES})
{pred_lines}

# Classes / rdf:type (sampled, unique up to {MAX_CLASSES})
{cls_lines}

# Sample triples (up to {SAMPLE_TRIPLES})
{sample_lines}
"""
    return summary.strip()

# ---------------------------------------------------------
# 3) Prompting LLM: NL -> SPARQL
# ---------------------------------------------------------
SPARQL_INSTRUCTIONS = """
You are an expert SPARQL 1.1 generator for a League of Legends knowledge graph.
Convert the user QUESTION into a valid SPARQL SELECT query.

DATABASE STRUCTURE EXAMPLE:
- Champions have a name: `?champion lol:championName "Yasuo"`.
- Spells belong to champions: `?spell lol:belongsToChampion ?champion`.
- Spells have a name: `?spell lol:spellName ?name` OR a tooltip: `?spell lol:spellTooltip ?text`.

CRITICAL RULES:
1. ALL variables MUST start with a question mark `?` (e.g., `?s`, `?p`, `?o`).
2. NEVER use a string literal like "Yasuo" directly with `lol:belongsToChampion`. 
   ALWAYS go through `lol:championName`.
   Example: `?s lol:belongsToChampion ?c . ?c lol:championName "Yasuo" .`
3. Use ONLY the prefixes provided in the SCHEMA.
4. Return ONLY the SPARQL query in a fenced code block ```sparql.
"""

def make_sparql_prompt(schema_summary: str, question: str) -> str:
    return f"""{SPARQL_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

QUESTION:
{question}

Return only the SPARQL query in a code block.
"""

CODE_BLOCK_RE = re.compile(r"```(?:sparql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

def extract_sparql_from_text(text: str) -> str:
    if not text: return ""
    m = CODE_BLOCK_RE.search(text)
    if m:
        return m.group(1).strip()
    return text.strip()

def generate_sparql(question: str, schema_summary: str) -> str:
    prompt = make_sparql_prompt(schema_summary, question)
    raw = ask_local_llm(prompt)
    query = extract_sparql_from_text(raw)
    return query

# ---------------------------------------------------------
# 4) Execute SPARQL with Self-Repair
# ---------------------------------------------------------
def run_sparql(g: Graph, query: str) -> Tuple[List[str], List[Tuple]]:
    res = g.query(query)
    vars_ = [str(v) for v in res.vars]
    rows = [tuple(str(cell) if cell is not None else "" for cell in r) for r in res]
    return vars_, rows

REPAIR_INSTRUCTIONS = """
The previous SPARQL failed to execute or returned nothing. Using the SCHEMA SUMMARY and ERROR MESSAGE,
return a corrected SPARQL 1.1 SELECT query. 

CRITICAL RULES:
- ALL variables MUST start with `?`.
- Do NOT link object properties directly to strings. Use data properties like `lol:championName` for string matching.
- Keep it simple.
- Return ONLY the corrected SPARQL in a single code block.
"""

def repair_sparql(schema_summary: str, question: str, bad_query: str, error_msg: str) -> str:
    prompt = f"""{REPAIR_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema_summary}

ORIGINAL QUESTION:
{question}

BAD SPARQL:
{bad_query}

ERROR MESSAGE:
{error_msg}

Return only the corrected SPARQL in a code block.
"""
    raw = ask_local_llm(prompt)
    return extract_sparql_from_text(raw)

def answer_with_sparql_generation(g: Graph, schema_summary: str, question: str, try_repair: bool = True) -> dict:
    sparql = generate_sparql(question, schema_summary)
    
    if not sparql:
        return {"query": "", "vars": [], "rows": [], "repaired": False, "error": "LLM returned empty response."}

    try:
        vars_, rows = run_sparql(g, sparql)
        return {"query": sparql, "vars": vars_, "rows": rows, "repaired": False, "error": None}
    except Exception as e:
        err = str(e)
        if try_repair:
            print(f"  [!] First query failed ({err}). Attempting self-repair...")
            repaired = repair_sparql(schema_summary, question, sparql, err)
            try:
                vars_, rows = run_sparql(g, repaired)
                return {"query": repaired, "vars": vars_, "rows": rows, "repaired": True, "error": None}
            except Exception as e2:
                return {"query": repaired, "vars": [], "rows": [], "repaired": True, "error": str(e2)}
        else:
            return {"query": sparql, "vars": [], "rows": [], "repaired": False, "error": err}

# ---------------------------------------------------------
# 5) Baseline: Direct LLM answer w/o KG
# ---------------------------------------------------------
def answer_no_rag(question: str) -> str:
    prompt = f"Answer the following question about League of Legends as best as you can:\n\n{question}"
    return ask_local_llm(prompt)

# ---------------------------------------------------------
# 6) CLI Demo
# ---------------------------------------------------------
def pretty_print_result(result: dict):
    if result.get("error"):
        print(f"\n[Execution Error] {result['error']}")
    
    print("\n[SPARQL Query Used]")
    print(result.get("query", ""))
    
    if result.get("repaired"):
        print("\n[!] The query was auto-repaired by the LLM.")
        
    vars_ = result.get("vars", [])
    rows = result.get("rows", [])
    
    if not rows and not result.get("error"):
        print("\n[No rows returned] The query executed successfully but found no data.")
        return
        
    if rows:
        print("\n[Results]")
        print(" | ".join(vars_))
        print("-" * (len(" | ".join(vars_)) + 5))
        for r in rows[:20]:
            print(" | ".join(r))
        if len(rows) > 20:
            print(f"... (showing 20 of {len(rows)})")

if __name__ == "__main__":
    print("="*60)
    print(" LoL Knowledge Graph RAG - Lab 6")
    print("="*60)
    
    g = load_graph(KG_FILE)
    print("Building schema summary for the LLM...")
    schema = build_schema_summary(g)
    
    print("\nSystem ready! (Type 'quit' to exit)")
    while True:
        q = input("\nQuestion: ").strip()
        if q.lower() in ["quit", "exit", "q"]:
            break
            
        print("\n--- Baseline (No RAG) ---")
        baseline_ans = answer_no_rag(q)
        print(baseline_ans)
        
        print(f"\n--- SPARQL-generation RAG ({LLM_MODEL} + rdflib) ---")
        result = answer_with_sparql_generation(g, schema, q, try_repair=True)
        pretty_print_result(result)
