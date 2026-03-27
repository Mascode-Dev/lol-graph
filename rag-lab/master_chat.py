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
            print(f"Error: {KG_PATH} not found.")
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
            return r.json().get("response", "Error")
        except:
            return "Connection Error"

    def get_sparql_context(self, question):
        prompt = f"""Write a SPARQL SELECT query. 
        Use ONLY these prefixes: {PREFIXES}

        FOOLPROOF TEMPLATES:
        - Spell Names: `?c lol:championName "Sett" . ?c lol:hasSpell ?s . ?s lol:spellName ?name .`
        - Spell Slot (Q,W,E,R): `?c lol:championName "Sett" . ?c lol:hasSpell ?s . ?s lol:spellSlot "Q" .`
        - Spell Cost: `?c lol:championName "Sett" . ?c lol:championName "Sett" . ?c lol:hasSpell ?s . ?s lol:spellSlot "Q" . ?s lol:cooldownBurn ?val .`
        - Passives: `?c lol:championName "Sett" . ?c lol:hasPassive ?p . ?p lol:spellDescription ?desc .`
        - Stats: `?c lol:championName "Sett" . ?c lol:hasStats ?st . ?st lol:attackrange ?val .`

        RULES:
        1. "Q", "W", "E", "R" are `lol:spellSlot`, NOT `lol:spellName`.
        2. "Cost" is `lol:costBurn`.
        3. Variables MUST start with `?`.
        4. Match the exact champion name (e.g., "Teemo").
        5. Return ONLY the code block.

        Question: {question}
        """
        query_raw = self.ask_llm(prompt).strip()
        match = re.search(r"```(?:sparql)?\s*(.*?)\s*```", query_raw, re.DOTALL | re.IGNORECASE)
        query_str = match.group(1).strip() if match else None
        
        if not query_str and "SELECT" in query_raw.upper():
            query_str = re.search(r"(SELECT.*)", query_raw, re.DOTALL | re.IGNORECASE).group(1).strip()

        if not query_str: return None, None
        if "PREFIX" not in query_str.upper(): query_str = PREFIXES + "\n" + query_str
            
        print(f"\n[Generated SPARQL]\n{query_str}")
        try:
            res = self.graph.query(query_str)
            results = [", ".join([f"{res.vars[i]}: {row[i]}" for i in range(len(res.vars))]) for row in res]
            if results: print(f"-> Found facts: {results}")
            return query_str, results
        except:
            return query_str, []

    def get_kge_prediction(self, champion_name):
        if not self.kge_model: return "No KGE."
        try:
            result = predict_target(model=self.kge_model, head=f"http://leagueoflegends.knowledge/champion/{champion_name.capitalize()}", 
                                    relation="http://leagueoflegends.knowledge/ontology#hasRole", triples_factory=self.training)
            return result.df.head(3).to_string()
        except: return "No prediction."

    def chat_loop(self):
        print("\n=== LoL Oracle Ready ===")
        while True:
            user_q = input("\nUser: ").strip()
            if not user_q or user_q.lower() in ['exit', 'quit']: break
            query, facts = self.get_sparql_context(user_q)
            
            if facts:
                context = "DATABASE FACTS:\n" + "\n".join(facts)
            else:
                match = re.search(r"([A-Z][a-z]+)", user_q)
                name = match.group(1) if match else "Aatrox"
                context = f"NO DATA FOUND. KGE PREDICTIONS FOR {name}:\n" + self.get_kge_prediction(name)

            final_prompt = f"""You are a League of Legends data bot.
            
            I have queried the database for you. 
            QUERY USED: {query}
            RESULTS FOUND: {context}
            
            USER QUESTION: {user_q}
            
            INSTRUCTION: Use the RESULTS FOUND to answer the QUESTION. 
            The variable names in the results (like 'val' or 'desc') correspond to what you asked for in the query.
            If the answer is there, state it clearly. If not, say you don't know.
            
            ANSWER:"""
            print("\nAI Oracle:", self.ask_llm(final_prompt))

if __name__ == "__main__":
    sys = LoL_RAG_System()
    sys.chat_loop()
