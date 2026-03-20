import os
import torch
import pandas as pd
import numpy as np
from pykeen.pipeline import PipelineResult
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
from rdflib import Graph, RDF, Namespace

def analyze_embeddings(model_dir, ontology_file):
    # Load model
    print("Loading model...")
    model = torch.load(os.path.join(model_dir, 'trained_model.pkl'), map_location=torch.device('cpu'), weights_only=False)
    
    # Load entity mappings
    print("Loading entity mappings...")
    entity_id_path = os.path.join(model_dir, 'training_triples', 'entity_to_id.tsv.gz')
    df_ent = pd.read_csv(entity_id_path, sep='\t')
    # The file has columns 'id' and 'label' (based on previous check)
    entity_to_id = dict(zip(df_ent['label'], df_ent['id']))
    id_to_entity = {v: k for k, v in entity_to_id.items()}
    
    # Get entity embeddings
    entity_embeddings = model.entity_representations[0](indices=None).detach().cpu().numpy()

    ### Nearest Neighbors
    print("\nFinding nearest neighbors for sample champions...")
    # Find any entity that looks like a champion
    potential_champs = ["ahri", "aatrox", "yasuo", "lux", "garen"]
    sample_entities = []
    for pc in potential_champs:
        # Find first entity that contains this name
        matches = [e for e in entity_to_id.keys() if pc in e.lower()]
        if matches:
            matches.sort(key=len)
            sample_entities.append(matches[0])
    
    for entity_uri in sample_entities:
        eid = entity_to_id[entity_uri]
        vec = entity_embeddings[eid]
        dists = np.linalg.norm(entity_embeddings - vec, axis=1)

        # Get top 6 (closest is the entity itself)
        nearest_ids = np.argsort(dists)[:6]
        
        print(f"\nNearest neighbors for {entity_uri}:")
        for nid in nearest_ids:
            print(f"  {id_to_entity[nid]} (dist: {dists[nid]:.4f})")

    ### t-SNE Clustering
    print("\nPreparing t-SNE visualization...")

    # Load ontology classes for coloring
    print("Parsing ontology for class mappings...")
    g = Graph()
    g.parse(ontology_file, format='turtle')
    
    # Map entities to their main class
    entity_classes = {}
    for s, p, o in g.triples((None, RDF.type, None)):
        s_str = str(s)
        # Use full URI for matching
        if s_str in entity_to_id:
            # Shorten class name for labeling
            cls_uri = str(o)
            cls_name = cls_uri.split('#')[-1].split('/')[-1]
            if cls_name in ['Champion', 'Spell', 'Skin', 'Role', 'Region', 'Position', 'Mechanic', 'CCEffect']:
                entity_classes[s_str] = cls_name

    selected_entities = list(entity_classes.keys())
    
    # Sample if too much entities
    if len(selected_entities) > 2000:
        import random
        random.seed(42)
        selected_entities = random.sample(selected_entities, 2000)
    
    if not selected_entities:
        print("Warning: No entities with class mappings found. Visualizing random subset.")
        selected_entities = list(entity_to_id.keys())[:1000]
        selected_labels = ["Unknown"] * len(selected_entities)
    else:
        selected_labels = [entity_classes[e] for e in selected_entities]
    
    selected_ids = np.array([entity_to_id[e] for e in selected_entities], dtype=int)
    X = entity_embeddings[selected_ids]

    print(f"Running t-SNE on {len(X)} entities...")
    tsne = TSNE(n_components=2, perplexity=30, max_iter=1000, random_state=42)
    X_embedded = tsne.fit_transform(X)

    # Plot
    plt.figure(figsize=(12, 10))
    sns.scatterplot(
        x=X_embedded[:, 0], y=X_embedded[:, 1],
        hue=selected_labels,
        palette="viridis",
        alpha=0.7,
        s=40
    )
    plt.title("t-SNE Visualization of LoL Knowledge Graph Embeddings (DistMult)")
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.tight_layout()
    
    os.makedirs("results/plots", exist_ok=True)
    plt_path = "results/plots/kge_tsne.png"
    plt.savefig(plt_path)
    print(f"Saved t-SNE plot to {plt_path}")

if __name__ == "__main__":
    analyze_embeddings("models/kge/DistMult", "lol_ontology_v3.ttl")
