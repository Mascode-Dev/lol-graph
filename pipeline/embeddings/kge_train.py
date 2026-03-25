import os
import torch
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory
import pandas as pd

def train_and_evaluate():
    # Load triples
    data_dir = "data/kge"
    train_path = os.path.join(data_dir, "train.txt")
    valid_path = os.path.join(data_dir, "valid.txt")
    test_path = os.path.join(data_dir, "test.txt")

    print("Loading triples...")
    training = TriplesFactory.from_path(train_path)
    validation = TriplesFactory.from_path(valid_path, entity_to_id=training.entity_to_id, relation_to_id=training.relation_to_id)
    testing = TriplesFactory.from_path(test_path, entity_to_id=training.entity_to_id, relation_to_id=training.relation_to_id)

    models = ["TransE", "DistMult"]
    results = []

    os.makedirs("results/kge", exist_ok=True)
    os.makedirs("models/kge", exist_ok=True)

    for model_name in models:
        print(f"\n--- Training {model_name} ---")
        
        # Hyperparameters
        result = pipeline(
            training=training,
            validation=validation,
            testing=testing,
            model=model_name,
            model_kwargs=dict(embedding_dim=100),
            training_kwargs=dict(num_epochs=200, use_tqdm=True),
            evaluation_kwargs=dict(use_tqdm=True),
            random_seed=42,
            device='cuda' if torch.cuda.is_available() else 'cpu'
        )

        # Save model
        model_path = f"models/kge/{model_name}.pth"
        result.save_to_directory(f"models/kge/{model_name}")
        
        # Extract metrics
        metrics = result.metric_results.to_dict()
        
        # Flatten some key metrics for comparison
        mrr = result.metric_results.get_metric('mrr')
        h1 = result.metric_results.get_metric('hits_at_1')
        h3 = result.metric_results.get_metric('hits_at_3')
        h10 = result.metric_results.get_metric('hits_at_10')

        results.append({
            "Model": model_name,
            "MRR": mrr,
            "Hits@1": h1,
            "Hits@3": h3,
            "Hits@10": h10
        })

    # Save results to CSV
    df = pd.DataFrame(results)
    df.to_csv("results/kge/comparison_results.csv", index=False)
    print("\nFinal Results Comparison:")
    print(df)

if __name__ == "__main__":
    train_and_evaluate()
