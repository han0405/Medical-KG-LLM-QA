import os
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class TuGraphQA:
    def __init__(self):
        # 1. 连接 TuGraph 
        uri = os.getenv('TUGRAPH_URI', 'bolt://59.110.166.54:7687')
        user = os.getenv('TUGRAPH_USERNAME', 'admin')
        password = os.getenv('TUGRAPH_PASSWORD', '73@TuGraph')
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # 2. 连接阿里云大模型
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if not api_key:
            raise ValueError("未找到 API Key，请检查环境变量")

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        print(f"系统初始化完成，已连接到 TuGraph: {uri}")
        self.schema = self.get_schema()

    def get_schema(self):
        """获取数据库真实的 Schema，用于构建 Prompt"""
        with self.driver.session(database='default') as session:
            try:
                # 获取节点标签
                v_res = session.run("CALL db.vertexLabels()")
                labels = [r[0] for r in v_res]
                
                # 获取关系标签
                e_res = session.run("CALL db.edgeLabels()")
                rels = [r[0] for r in e_res]
                
                schema_info = f"Node Labels: {labels}\nRelationship Types: {rels}"
                print(f"读取到数据库 Schema:\n{schema_info}")
                return schema_info
            except Exception as e:
                print(f"获取 Schema 失败: {e}")
                return "Schema fetch failed"

    def generate_cypher(self, question):
        """让大模型将自然语言转为 Cypher"""
        prompt = f"""你是一个 TuGraph 图数据库查询专家。
请根据以下 Schema 编写 Cypher 查询语句。

Database Schema:
{self.schema}

Schema 解释:
- Disease (疾病) 节点包含 name 属性
- Symptom (症状) 节点包含 name 属性
- 它们通过 HAS_SYMPTOM 关系连接: (:Disease)-[:HAS_SYMPTOM]->(:Symptom)

用户问题: "{question}"

要求:
1. 仅输出 Cypher 语句，不要有任何 Markdown 标记或解释。
2. 使用 CONTAINS 进行模糊匹配以提高召回率。
3. 限制返回结果数量 (LIMIT 10)。

示例:
问: 感冒有什么症状?
Cypher: MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) WHERE d.name CONTAINS '感冒' RETURN s.name

问: 什么病会导致头痛?
Cypher: MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) WHERE s.name CONTAINS '头痛' RETURN d.name

生成的 Cypher:"""

        response = self.client.chat.completions.create(
            model="qwen-plus",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content.strip()

    def execute_query(self, cypher):
        """执行 Cypher 查询"""
        with self.driver.session(database='default') as session:
            result = session.run(cypher)
            return [r.values()[0] for r in result]

    def answer_question(self, question):
        print(f"\n{'='*40}")
        print(f"用户提问: {question}")
        print(f"{'='*40}")
        
        # 1. 生成 Cypher
        cypher = self.generate_cypher(question)
        print(f"[1] 生成的 Cypher 语句:\n{cypher}")
        
        # 2. 查询数据库
        try:
            results = self.execute_query(cypher)
            print(f"[2] 数据库返回结果数: {len(results)}")
            
            if not results:
                print("    (未找到匹配结果)")
                final_answer = "抱歉，数据库中没有找到相关信息。"
            else:
                # 3. 生成最终回复
                context = ",".join([str(r) for r in results[:20]]) # 限制上下文长度
                summary_prompt = f"用户问：'{question}'。数据库查询结果为：{context}。请用自然流畅的中文回答用户，列举主要几项即可。"
                
                resp = self.client.chat.completions.create(
                    model="qwen-plus",
                    messages=[{"role": "user", "content": summary_prompt}],
                    temperature=0.5
                )
                final_answer = resp.choices[0].message.content.strip()
                
            print(f"[3] 最终回答:\n{final_answer}")
            
        except Exception as e:
            print(f"[Error] 查询执行失败: {e}")

    def close(self):
        self.driver.close()

if __name__ == "__main__":
    qa = TuGraphQA()
    
    # 测试两个问题：一个是正向查症状，一个是反向查疾病
    questions = [
        "腰椎间盘突出有哪些症状？",  # 测试 diseases.csv 的数据
        "什么病会导致肚子疼？"      # 测试 disease_details.csv 的数据 
    ]
    
    for q in questions:
        qa.answer_question(q)
        
    qa.close()