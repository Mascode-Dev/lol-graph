import torch
import requests
import json
import re
import os
import sys
from rdflib import Graph
from pykeen.predict import predict_target
from pykeen.triples import TriplesFactory

# --- Configuration ---
KG_PATH = "data/processed/final_kb.nt"
KGE_MODEL_DIR = "models/kge/DistMult"
KGE_TRAIN_PATH = "data/kge/train.txt"
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "llama3.1"

PREFIXES = """
PREFIX lol: <http://leagueoflegends.knowledge/ontology#>
PREFIX champ: <http://leagueoflegends.knowledge/champion/>
PREFIX spell: <http://leagueoflegends.knowledge/spell/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

class LoL_RAG_System:
    def __init__(self):
        print("Initializing LoL Master RAG...")
        if not os.path.exists(KG_PATH):
            print(f"Error: {KG_PATH} not found. Run finalize_kb.py first.")
            sys.exit(1)
            
        self.graph = Graph()
        self.graph.parse(KG_PATH, format="nt")
        print(f"Loaded KG: {len(self.graph)} triples.")

        if os.path.exists(KGE_TRAIN_PATH):
            self.training = TriplesFactory.from_path(KGE_TRAIN_PATH)
            self.kge_model = torch.load(os.path.join(KGE_MODEL_DIR, 'trained_model.pkl'), 
                                       map_location=torch.device('cpu'), weights_only=False)
            print("Loaded KGE Model (DistMult).")
        else:
            self.kge_model = None

    def ask_llm(self, prompt):
        payload = {"model": LLM_MODEL, "prompt": prompt, "stream": False}
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=30)
            if r.status_code != 200:
                return f"Error: Ollama returned status {r.status_code}"
            return r.json().get("response", "No response field in JSON.")
        except requests.exceptions.RequestException as e:
            return f"Error: Could not connect to Ollama ({e}). Ensure it is running."

    def get_sparql_context(self, question):
        prompt = f"""Generate a SPARQL 1.1 SELECT query for a League of Legends knowledge graph.

EXHAUSTIVE GRAPH SCHEMA (Use EXACTLY these paths):

1. CHAMPIONS
?champ a lol:Champion .
?champ lol:championName "ChampionName" .
?champ lol:championTitle ?title .
?champ lol:lore ?lore .

2. SPELLS (Q, W, E, R)
?champ lol:hasSpell ?spell .
?spell lol:spellName ?spellName .
?spell lol:spellSlot ?slot .       # e.g., "Q", "W", "E", "R"
?spell lol:spellDescription ?spellDesc .
?spell lol:cooldownBurn ?cooldown .
?spell lol:costBurn ?cost .
?spell lol:rangeBurn ?range .

3. PASSIVE ABILITY
?champ lol:hasPassive ?passive .
?passive lol:spellName ?passiveName .
?passive lol:spellDescription ?passiveDesc .

4. STATS (Health, Armor, Attack Range, etc.)
?champ lol:hasStats ?stats .
?stats lol:hp ?hp .
?stats lol:attackrange ?attackrange .
?stats lol:armor ?armor .

5. ROLE & REGION
?champ lol:hasRole ?role . ?role lol:roleName ?roleName .
?champ lol:isFromRegion ?reg . ?reg lol:regionName ?regName .

PREFIXES:
{PREFIXES}

RULES:
1. EVERY variable MUST start with `?` (e.g. `?champ`, `?spellDesc`). NO EXCEPTIONS.
2. Replace "ChampionName" with the exact name (e.g., "Sett", "Fiddlesticks").
3. SELECT the specific variable you are looking for.
4. Return ONLY the raw SPARQL query code block.

User Question: {question}
"""
        query_raw = self.ask_llm(prompt).strip()
        
        query_str = None
        match = re.search(r"```(?:sparql)?\s*(.*?)\s*```", query_raw, re.DOTALL | re.IGNORECASE)
        if match:
            query_str = match.group(1).strip()
        elif "SELECT" in query_raw.upper():
            select_match = re.search(r"(SELECT.*)", query_raw, re.DOTALL | re.IGNORECASE)
            if select_match:
                query_str = select_match.group(1).strip()

        if not query_str:
            return None, None

        # Nuclear auto-fixer: force '?' on obvious variables if LLM forgot
        lines = query_str.split('\n')
        fixed_lines = []
        possible_vars = ['champ', 'spell', 'passive', 'stats', 'role', 'reg', 'slot', 'cooldown', 'cost', 'range', 'hp', 'attackrange', 'armor', 'roleName', 'regName', 'spellName', 'spellDesc', 'passiveName', 'passiveDesc', 'title', 'lore']
        for line in lines:
            words = line.split()
            fixed_words = []
            for w in words:
                clean_w = w.rstrip('.').rstrip(';')
                if clean_w in possible_vars:
                    fixed_words.append("?" + w)
                else:
                    fixed_words.append(w)
            fixed_lines.append(" ".join(fixed_words))
        query_str = "\n".join(fixed_lines)

        if "PREFIX" not in query_str.upper():
            query_str = PREFIXES + "\n" + query_str
            
        print(f"\n[Generated SPARQL]\n{query_str}")
        
        try:
            res = self.graph.query(query_str)
            vars_names = [str(v) for v in res.vars]
            results = []
            for row in res:
                row_data = [f"{vars_names[i]}: {row[i]}" for i in range(len(vars_names))]
                results.append(" | ".join(row_data))
            
            if results:
                print(f"-> Found facts: {results}")
            return query_str, results
        except Exception as e:
            print(f"SPARQL Error: {e}")
            return query_str, []

    def get_kge_prediction(self, champion_name, relation_uri):
        if not self.kge_model: return "KGE Model not loaded."
        champ_uri = f"http://leagueoflegends.knowledge/champion/{champion_name.capitalize()}"
        try:
            result = predict_target(model=self.kge_model, head=champ_uri, relation=relation_uri, triples_factory=self.training)
            return result.df.head(5).to_string()
        except Exception as e:
            return f"Prediction failed: {e}"

    def chat_loop(self):
        print("\n=== LoL AI Oracle Ready ===")
        print("Type your question or 'exit' to stop.")
        while True:
            user_q = input("\nUser: ").strip()
            if not user_q: continue
            if user_q.lower() in ['exit', 'quit']: break

            query, facts = self.get_sparql_context(user_q)
            
            context = ""
            if facts:
                context = f"THE FOLLOWING ARE FACTS FROM THE DATABASE:\n" + "\n".join(facts)
            else:
                match = re.search(r"([A-Z][a-z]+)", user_q)
                name = match.group(1) if match else "Aatrox"
                pred = self.get_kge_prediction(name, "http://leagueoflegends.knowledge/ontology#hasRole")
                context = f"NO DIRECT FACTS FOUND. PREDICTIONS FOR {name} ROLE:\n{pred}"

            final_prompt = f"""You are a strict data-reporting robot.
            
            1. Answer the User Question using ONLY the DATA provided.
            2. Do not add outside knowledge.
            3. If DATA contains the answer, output it directly.
            
            DATA:
            {context}

            QUESTION: {user_q}
            ANSWER:"""
            
            print("\nAI Oracle:", self.ask_llm(final_prompt))

if __name__ == "__main__":
    try:
        sys = LoL_RAG_System()
        sys.chat_loop()
    except KeyboardInterrupt:
        print("\nExiting...")
