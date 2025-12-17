# Medical-KG-LLM-QA

A Medical Knowledge Graph QA System built with Neo4j, TuGraph, and LLMs (Qwen-Plus). Features structural extraction, graph construction, and Text-to-Cypher natural language querying.

基于大模型的医疗知识图谱构建与问答系统 (Medical KG & QA System)。本项目旨在构建一个垂直领域的医疗知识图谱，并结合大语言模型（LLM）实现自然语言问答（Text-to-Cypher）。项目涵盖了从非结构化文本提取、图数据库存储（Neo4j & TuGraph）到智能问答接口开发的全流程。

##  项目结构 (Project Structure)

```text
Project/
├── data/                            # 数据文件目录
│   ├── diseases.csv                 # 疾病基础信息表 (39健康网采集)
│   ├── disease_details.csv          # 疾病详细信息表
│   └── symptoms.csv                 # 症状表
│
├── src/                             # 源代码目录
│   ├── experiment_extraction.py     # Task 2: 基于LLM的结构化数据提取实验
│   ├── import_to_neo4j.py           # Task 3: Neo4j 数据导入脚本
│   ├── neo4j_llm_interface.py       # Task 3: Neo4j 问答接口 (LangChain/Driver实现)
│   ├── import_to_aliyun_tugraph.py  # Task 4: TuGraph 数据导入脚本 (适配阿里云环境)
│   └── experiment_tugraph_final.py  # Task 4: TuGraph 问答接口 (最终版)
│
├── requirements.txt                 # 项目依赖
└── README.md                        # 项目说明文档
```

##环境依赖 (Requirements)

```text
Python: 3.8+

数据库 (Databases):

Neo4j Community Server (v5.x)

TuGraph (Aliyun/Docker)

核心库 (Core Libraries):

neo4j, langchain, openai, pandas, python-dotenv
```
