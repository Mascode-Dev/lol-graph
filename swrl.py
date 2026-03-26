import os
from owlready2 import *
from rdflib import Graph

# 1. Configuration des chemins
ttl_path = "lol_ontology_v3.ttl"
rdf_xml_path = "lol_ontology_v3.owl"

# 2. Conversion Turtle -> RDF/XML (pour une compatibilité parfaite avec Owlready2)
print("Conversion du format Turtle vers RDF/XML...")
g = Graph()
g.parse(ttl_path, format="turtle")
g.serialize(destination=rdf_xml_path, format="xml")

# 3. Chargement de l'ontologie et des espaces de noms
onto = get_ontology(f"file://{os.path.abspath(rdf_xml_path)}").load()

# Définition des namespaces tels qu'ils apparaissent dans votre fichier .ttl
lol = onto.get_namespace("http://leagueoflegends.knowledge/ontology#")
mech = onto.get_namespace("http://leagueoflegends.knowledge/mechanic/")
cc = onto.get_namespace("http://leagueoflegends.knowledge/cc_effect/")
style = onto.get_namespace("http://leagueoflegends.knowledge/playstyle/")

# Pour SWRL, on s'assure que les namespaces ont le bon nom (utilisé comme préfixe dans la règle)
lol.name = "lol"
mech.name = "mech"
cc.name = "cc"
style.name = "style"

print(f"DEBUG: lol.name = {lol.name}")
print(f"DEBUG: mech.name = {mech.name}")
print(f"DEBUG: cc.name = {cc.name}")
print(f"DEBUG: style.name = {style.name}")

print(f"DEBUG: lol.Champion = {lol.Champion}")
print(f"DEBUG: getattr(lol, 'Champion') = {getattr(lol, 'Champion', None)}")
print(f"DEBUG: mech.Dash = {mech.Dash}")
print(f"DEBUG: cc.Stun = {cc.Stun}")

with onto:
    # 4. Création de l'individu 'Engager' s'il n'existe pas encore
    if not style.Engager:
        # PlaystyleTag est une classe dans le namespace 'lol'
        engager = lol.PlaystyleTag("Engager", namespace = style)
        engager.playstyleTagName = ["Engager"]

    # 5. Définition de la règle SWRL
    # On utilise les préfixes définis ci-dessus
    rule = Imp()
    rule.set_as_rule("""
        Champion(?c) ^ 
        champHasMechanic(?c, Dash) ^ 
        champHasCCEffect(?c, Stun) 
        -> hasPlaystyleTag(?c, Engager)
    """, namespaces = [lol, mech, cc, style])

print("Lancement du raisonneur Pellet...")
with onto:
    # sync_reasoner_pellet effectue l'inférence SWRL
    sync_reasoner_pellet(infer_property_values = True, infer_data_property_values = True)

# 6. Vérification du résultat (Exemple avec un champion ayant un Dash et un Stun)
print("\n--- Résultats des inférences ---")
for champ in lol.Champion.instances():
    tags = champ.hasPlaystyleTag
    if any("Engager" in str(t) for t in tags):
        print(f"Inférence réussie : {champ.name} est maintenant tagué comme 'Engager' !")

# 7. Sauvegarde
onto.save(file = "data/processed/final_kb_reasoned.owl", format = "rdfxml")
print("\nOntologie enrichie sauvegardée dans data/processed/final_kb_reasoned.owl")