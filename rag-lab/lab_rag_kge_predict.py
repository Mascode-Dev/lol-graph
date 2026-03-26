import torch
from pykeen import predict
from pykeen.triples import TriplesFactory
import os

# 1. Setup paths
MODEL_DIR = "models/kge/DistMult"
TRAIN_PATH = "data/kge/train.txt"

def load_kge_system():
    print("Loading KGE training factory and model...")
    training = TriplesFactory.from_path(TRAIN_PATH)
    # Load the model from the directory where it was saved
    model = torch.load(os.path.join(MODEL_DIR, 'trained_model.pkl'), map_location=torch.device('cpu'), weights_only=False)
    return training, model

def predict_top_k(training, model, head_label, relation_label, k=5):
    """Predicts the most likely tail entities for a given head and relation."""
    try:
        from pykeen.predict import predict_target
        
        result = predict_target(
            model=model,
            head=head_label,
            relation=relation_label,
            triples_factory=training,
        )
        return result.df.head(k)
    except Exception as e:
        print(f"Error in prediction: {e}")
        return None

def rag_kge_demo():
    training, model = load_kge_system()
    
    print("\n--- KGE Predictive RAG Demo ---")
    print("Example: Predicting attributes for 'Aatrox'")
    
    # Example 1: What is the role of Aatrox?
    head = "http://leagueoflegends.knowledge/champion/Aatrox"
    rel = "http://leagueoflegends.knowledge/ontology#hasRole"
    
    print(f"\nQuery: {head} -- {rel} --> ?")
    top_tails = predict_top_k(training, model, head, rel)
    
    if top_tails is not None:
        print("\nTop Predicted Tails:")
        print(top_tails[['tail_label', 'score']])

    # Example 2: What is a related entity for a champion via a Wikidata property?
    # Using one of the filtered Wikidata properties
    head = "http://www.wikidata.org/entity/Q223341" # Aatrox Wikidata ID
    rel = "http://www.wikidata.org/prop/direct/P674" # 'characters' / 'has character'
    
    print(f"\nQuery (Wikidata): {head} -- {rel} --> ?")
    top_wikidata = predict_top_k(training, model, head, rel)
    if top_wikidata is not None:
        print("\nTop Predicted Wikidata Tails:")
        print(top_wikidata[['tail_label', 'score']])

if __name__ == "__main__":
    rag_kge_demo()
