from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from neo4j import GraphDatabase
import json

API_KEY = "sk-"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = ""
GRAPH_SCHEMA = """
Node labels:
  - Disease (properties: name, aliases, description, website)
  - Symptom (properties: name, aliases, description, website)

Relationship types:
  - HAS_SYMPTOM: connects Disease to Symptom

Statistics:
  - 237 Disease nodes
  - 675 Symptom nodes  
  - 521 HAS_SYMPTOM relationships
"""

CYPHER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["schema", "question"],
    template="""
You are an expert in converting natural language questions to Neo4j Cypher queries.

Graph Schema:
{schema}

Instructions:
- Use only the node labels and relationship types from the schema above
- For Chinese medical terms, use exact string matching with the name property
- Return ONLY the Cypher query without any explanation or markdown formatting
- Add LIMIT clause to restrict results when appropriate

Few-shot Examples:

Question: 糖尿病有哪些症状？
Cypher: MATCH (d:Disease {{name: '糖尿病'}})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name LIMIT 20

Question: 哪些疾病会导致头晕？  
Cypher: MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom {{name: '头晕'}}) RETURN d.name LIMIT 20

Question: 腰椎间盘突出的症状
Cypher: MATCH (d:Disease {{name: '腰椎间盘突出'}})-[:HAS_SYMPTOM]->(s:Symptom) RETURN s.name LIMIT 20

Now generate the Cypher query for this question:

Question: {question}

Cypher Query:
"""
)

ANSWER_GENERATION_PROMPT = PromptTemplate(
    input_variables=["question", "context"],
    template="""
You are a medical knowledge assistant. Based on the query results from the knowledge graph, provide a clear and accurate answer in Chinese.

Question: {question}

Database Query Results:
{context}

Please provide a natural, informative answer based on the results above. If there are no results, politely state that the information is not available in the database.

Answer:
"""
)

class MedicalKnowledgeGraphQA:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password, api_key, base_url):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.llm = ChatOpenAI(
            model="qwen-plus",
            temperature=0,
            api_key=api_key,
            base_url=base_url
        )
        self.schema = GRAPH_SCHEMA
        self.cypher_chain = CYPHER_GENERATION_PROMPT | self.llm
        self.answer_chain = ANSWER_GENERATION_PROMPT | self.llm
    
    def close(self):
        self.driver.close()
    
    def generate_cypher(self, question):
        response = self.cypher_chain.invoke({
            "schema": self.schema,
            "question": question
        })
        cypher = response.content.strip()
        cypher = cypher.replace("```cypher", "").replace("```", "").strip()
        return cypher
    
    def execute_cypher(self, cypher):
        with self.driver.session() as session:
            result = session.run(cypher)
            records = [record.data() for record in result]
            return records
    
    def generate_answer(self, question, context):
        response = self.answer_chain.invoke({
            "question": question,
            "context": json.dumps(context, ensure_ascii=False, indent=2)
        })
        return response.content.strip()
    
    def query(self, question):
        print(f"\nQuestion: {question}")
        
        try:
            cypher_query = self.generate_cypher(question)
            print(f"\n[Step 1] Generated Cypher Query:")
            print(f"{cypher_query}")
            
            db_results = self.execute_cypher(cypher_query)
            print(f"\n[Step 2] Database Query Results:")
            print(f"Found {len(db_results)} results")
            for idx, record in enumerate(db_results[:10], 1):
                print(f"  {idx}. {record}")
            if len(db_results) > 10:
                print(f"  ... and {len(db_results) - 10} more results")
            
            final_answer = self.generate_answer(question, db_results[:20])
            print(f"\n[Step 3] Generated Natural Language Answer:")
            print(f"{final_answer}")
            
            print(f"\n✓ Status: SUCCESS")
            
            return {
                "question": question,
                "cypher": cypher_query,
                "intermediate_steps": [
                    {"query": cypher_query},
                    {"context": db_results}
                ],
                "result": final_answer
            }
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return None

def main():
    print("Task 3: Neo4j + LLM Interface for Natural Language to Cypher")
    
    print("\nInitializing Medical Knowledge Graph QA System...")
    
    qa_system = MedicalKnowledgeGraphQA(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        api_key=API_KEY,
        base_url=BASE_URL
    )
    
    print(f"\nGraph Schema Information:")
    print(GRAPH_SCHEMA)
    
    test_questions = [
        "宫外孕有哪些症状？",
        "腰椎间盘突出的症状有哪些？",
        "哪些疾病会导致胃疼？"
    ]
    
    print("\n" + "=" * 70)
    print("Running Test Cases: Natural Language → Cypher → Results → Answer")

    
    results = []
    for idx, question in enumerate(test_questions, 1):
        print(f"[Test Case {idx}/{len(test_questions)}]")
        
        result = qa_system.query(question)
        if result:
            results.append(result)
        
    qa_system.close()
    
    print("Testing Completed Successfully!")
    print(f"\nSuccessful conversions: {len(results)}/{len(test_questions)}")
 
    return results

if __name__ == "__main__":
    main()