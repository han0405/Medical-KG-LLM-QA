import os
import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

class TuGraphImporter:
    def __init__(self):
        # 配置连接信息
        uri = os.getenv('TUGRAPH_URI', 'bolt://59.110.166.54:7687')
        user = os.getenv('TUGRAPH_USERNAME', 'admin')
        password = os.getenv('TUGRAPH_PASSWORD', '73@TuGraph')
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            # 测试连接
            with self.driver.session(database='default') as session:
                session.run("RETURN 1")
            print(f"成功连接到 TuGraph: {uri}")
        except Exception as e:
            print(f"连接失败: {e}")
            raise e

    def init_schema(self):
        """初始化数据库 Schema"""
        print("开始初始化 Schema...")
        with self.driver.session(database='default') as session:
            try:
                # 清除旧数据
                session.run("MATCH (n) DETACH DELETE n")
                
                # 创建标签 (TuGraph 必须步骤，忽略已存在错误)
                try: session.run("CALL db.createVertexLabel('Disease', 'name', 'name', 'STRING', false)")
                except: pass
                
                try: session.run("CALL db.createVertexLabel('Symptom', 'name', 'name', 'STRING', false)")
                except: pass
                
                try: session.run("CALL db.createEdgeLabel('HAS_SYMPTOM', '[[\"Disease\", \"Symptom\"]]')")
                except: pass
                
                print("Schema 初始化完成")
            except Exception as e:
                print(f"Schema 初始化异常: {e}")

    def _get_csv_reader(self, file_path, expected_col):
        """尝试不同编码读取文件"""
        encodings = ['utf-8-sig', 'gbk', 'utf-8']
        
        for enc in encodings:
            try:
                f = open(file_path, 'r', encoding=enc)
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                
                # 检查关键列名
                if expected_col in headers or 'Name' in headers or '疾病名称' in headers:
                    return f, reader
                else:
                    f.close()
            except UnicodeDecodeError:
                if 'f' in locals(): f.close()
                continue
        
        print(f"错误: 在 {file_path} 中无法识别表头")
        return None, None

    def import_data(self, diseases_csv, details_csv):
        print("开始导入数据...")
        with self.driver.session(database='default') as session:
            
            # 1. 处理主要疾病表
            f, reader = self._get_csv_reader(diseases_csv, '疾病名称')
            if f and reader:
                count = 0
                for row in reader:
                    d_name = row.get('疾病名称') or row.get('Name')
                    if not d_name: continue
                    d_name = d_name.strip()

                    session.run("MERGE (d:Disease {name: $name})", name=d_name)
                    
                    # 动态处理分列的症状
                    for col, val in row.items():
                        # 筛选包含'症状'的列，且排除元数据列
                        if col and ('症状' in col or 'Symptom' in col) and val and val.strip():
                            if col in ['疾病名称', 'Name', '网址', '别名', '描述']: continue
                            
                            s_name = val.strip()
                            session.run("MERGE (s:Symptom {name: $name})", name=s_name)
                            session.run("""
                                MATCH (d:Disease {name: $d_name})
                                MATCH (s:Symptom {name: $s_name})
                                MERGE (d)-[:HAS_SYMPTOM]->(s)
                            """, d_name=d_name, s_name=s_name)
                    
                    count += 1
                
                f.close()
                print(f"主要疾病表导入完成，共处理 {count} 条数据")
            else:
                print("跳过主要疾病表导入")

            # 2. 处理疾病详情表
            f, reader = self._get_csv_reader(details_csv, '典型症状')
            if f and reader:
                count = 0
                for row in reader:
                    d_name = row.get('疾病名称') or row.get('Name')
                    if not d_name: continue
                    d_name = d_name.strip()

                    session.run("MERGE (d:Disease {name: $name})", name=d_name)

                    # 处理逗号分隔的症状列
                    s_str = row.get('典型症状') or row.get('症状') or row.get('Typical Symptoms')
                    if s_str:
                        s_list = [s.strip() for s in s_str.replace('，', ',').split(',') if s.strip()]
                        for s_name in s_list:
                            session.run("MERGE (s:Symptom {name: $name})", name=s_name)
                            session.run("""
                                MATCH (d:Disease {name: $d_name})
                                MATCH (s:Symptom {name: $s_name})
                                MERGE (d)-[:HAS_SYMPTOM]->(s)
                            """, d_name=d_name, s_name=s_name)
                    
                    count += 1
                
                f.close()
                print(f"详情表导入完成，共处理 {count} 条数据")
            else:
                print("跳过详情表导入")

    def verify(self):
        print("正在验证导入结果...")
        with self.driver.session(database='default') as session:
            try:
                d_num = session.run("MATCH (n:Disease) RETURN count(n) as c").single()['c']
                s_num = session.run("MATCH (n:Symptom) RETURN count(n) as c").single()['c']
                r_num = session.run("MATCH ()-[r:HAS_SYMPTOM]->() RETURN count(r) as c").single()['c']
                
                print(f"统计结果:\n - Disease 节点: {d_num}\n - Symptom 节点: {s_num}\n - 关系数量: {r_num}")
                
                if d_num == 0:
                    print("警告: 数据库为空")
            except Exception as e:
                print(f"验证过程出错: {e}")

    def close(self):
        self.driver.close()

if __name__ == "__main__":
    importer = TuGraphImporter()
    
    file1 = 'data/diseases.csv'
    file2 = 'data/disease_details.csv'
    
    if os.path.exists(file1) and os.path.exists(file2):
        importer.init_schema()
        importer.import_data(file1, file2)
        importer.verify()
    else:
        print("CSV文件未找到，请检查路径")
    
    importer.close()