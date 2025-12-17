import pandas as pd
from py2neo import Graph, Node, Relationship
import os

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = ""

DATA_DIR = "../data"

print("Connecting to Neo4j...")
graph = Graph(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("Clearing existing data...")
graph.run("MATCH (n) DETACH DELETE n")

print("\nReading CSV files...")

def read_csv_auto_encoding(filepath):
    encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
    for encoding in encodings:
        try:
            return pd.read_csv(filepath, encoding=encoding)
        except:
            continue
    raise Exception(f"Cannot read {filepath} with any encoding")

diseases_df = read_csv_auto_encoding(os.path.join(DATA_DIR, "diseases.csv"))
symptoms_df = read_csv_auto_encoding(os.path.join(DATA_DIR, "symptoms.csv"))
disease_details_df = read_csv_auto_encoding(os.path.join(DATA_DIR, "disease_details.csv"))

print(f"Loaded {len(diseases_df)} diseases")
print(f"Loaded {len(symptoms_df)} symptoms")
print(f"Loaded {len(disease_details_df)} disease details")

print("\nCreating Disease nodes...")
disease_count = 0
for idx, row in diseases_df.iterrows():
    disease_node = Node(
        "Disease",
        name=str(row['Name']),
        website=str(row.get('Website', '')),
        aliases=str(row.get('Aliases', '')),
        description=str(row.get('Description', ''))
    )
    graph.create(disease_node)
    disease_count += 1
    if disease_count % 100 == 0:
        print(f"  Created {disease_count} disease nodes...")

print(f"Total disease nodes created: {disease_count}")

print("\nCreating Symptom nodes...")
symptom_count = 0
for idx, row in symptoms_df.iterrows():
    symptom_node = Node(
        "Symptom",
        name=str(row['Name']),
        website=str(row.get('Website', '')),
        aliases=str(row.get('Aliases', '')),
        description=str(row.get('Description', ''))
    )
    graph.create(symptom_node)
    symptom_count += 1
    if symptom_count % 100 == 0:
        print(f"  Created {symptom_count} symptom nodes...")

print(f"Total symptom nodes created: {symptom_count}")

print("\nCreating Disease-Symptom relationships from diseases.csv...")
rel_count_1 = 0
for idx, row in diseases_df.iterrows():
    disease_name = str(row['Name'])
    
    symptom_columns = ['Related Symptom 1', 'Related Symptom 2', 
                      'Related Symptom 3', 'Related Symptom 4']
    
    for col in symptom_columns:
        if col in row and pd.notna(row[col]) and str(row[col]).strip():
            symptom_name = str(row[col]).strip()
            
            query = """
            MATCH (d:Disease {name: $disease_name})
            MATCH (s:Symptom {name: $symptom_name})
            MERGE (d)-[:HAS_SYMPTOM]->(s)
            """
            try:
                graph.run(query, disease_name=disease_name, symptom_name=symptom_name)
                rel_count_1 += 1
            except:
                pass
    
    if (idx + 1) % 100 == 0:
        print(f"  Processed {idx + 1} diseases...")

print(f"Created {rel_count_1} Disease-Symptom relationships from diseases.csv")

print("\nCreating Disease-Symptom relationships from disease_details.csv...")
rel_count_2 = 0
for idx, row in disease_details_df.iterrows():
    disease_name = str(row['Name'])
    typical_symptoms = str(row.get('Typical Symptoms', ''))
    
    if pd.notna(typical_symptoms) and typical_symptoms.strip():
        symptom_list = typical_symptoms.replace('\t', '').replace('\n', '').split('、')
        
        for symptom in symptom_list:
            symptom = symptom.strip()
            if symptom:
                query = """
                MATCH (d:Disease {name: $disease_name})
                MATCH (s:Symptom {name: $symptom_name})
                MERGE (d)-[:HAS_SYMPTOM]->(s)
                """
                try:
                    graph.run(query, disease_name=disease_name, symptom_name=symptom)
                    rel_count_2 += 1
                except:
                    pass
    
    if (idx + 1) % 50 == 0:
        print(f"  Processed {idx + 1} disease details...")

print(f"Created {rel_count_2} Disease-Symptom relationships from disease_details.csv")

print("\n" + "="*70)
print("Data import completed!")
print("="*70)

print("\nVerifying data...")
result = graph.run("MATCH (d:Disease) RETURN count(d) as count").data()
print(f"Total Disease nodes: {result[0]['count']}")

result = graph.run("MATCH (s:Symptom) RETURN count(s) as count").data()
print(f"Total Symptom nodes: {result[0]['count']}")

result = graph.run("MATCH ()-[r:HAS_SYMPTOM]->() RETURN count(r) as count").data()
print(f"Total HAS_SYMPTOM relationships: {result[0]['count']}")

print("\nSample query test:")
result = graph.run("""
MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
RETURN d.name as disease, s.name as symptom
LIMIT 5
""").data()

for record in result:
    print(f"  {record['disease']} -> {record['symptom']}")

print("\n" + "="*70)
print("Import and verification successful!")
print("="*70)