# coding=utf-8
import pandas as pd
from langchain_openai import ChatOpenAI
from kor.extraction import create_extraction_chain
from kor.nodes import Object, Text

# 配置 API 信息
API_KEY = "sk-" 
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 模拟输入文本 (来自你的数据集截图：肾阴虚描述)
test_text = """
肾阴虚，是肾脏阴液不足表现的证候，多由久病伤肾，或禀赋不足房事过度，或过服温燥劫阴之品所致。
临床表现：腰膝酸痛，头晕耳鸣，失眠多梦，五心烦热，潮热盗汗，遗精早泄，咽干颧红，舌红少津无苔，脉细数等。
"""

# 定义三种不同的 Prompt 策略 (通过修改 Schema 描述实现)
prompt_strategies = {
    "Strategy_1_Basic": "从文本中提取疾病信息，包括名称、成因和症状。",
    "Strategy_2_RolePlay": "你是一位资深中医数据分析师。请从临床描述中精准提取关键医疗实体，确保专业性和准确性。",
    "Strategy_3_Strict": "仅提取明确提及的实体。忽略所有修饰性形容词。如果文本中未提及，请不要编造信息。"
}

# 定义三种不同的 Temperature
temperatures = [0, 0.5, 1.0]

results = []

print("开始执行提取实验 (3种 Temperature x 3种 Prompt)...")
print("-" * 50)

for temp in temperatures:
    for p_name, p_desc in prompt_strategies.items():
        print(f"Testing: Temp={temp}, Prompt={p_name}")
        
        # 1. 初始化 LLM
        llm = ChatOpenAI(
            model="qwen-plus",
            temperature=temp,
            api_key=API_KEY,
            base_url=BASE_URL
        )

        # 2. 动态定义 Schema (根据当前的 Prompt 策略)
        disease_schema = Object(
            id="disease_info",
            description=p_desc, # 这里动态插入不同的 Prompt 描述
            attributes=[
                Text(id="name", description="疾病名称"),
                Text(id="cause", description="发病原因"),
                Text(id="symptom", description="临床表现/症状")
            ],
            examples=[] # 为简化实验，此处不使用 Few-shot 示例，纯测 Prompt 效果
        )

        # 3. 创建并执行 Chain
        try:
            chain = create_extraction_chain(llm, disease_schema)
            output = chain.invoke(test_text)['data']
            
            # 记录结果
            results.append({
                "Temperature": temp,
                "Prompt_Strategy": p_name,
                "Extracted_Data": output
            })
        except Exception as e:
            print(f"Error: {e}")

print("-" * 50)
print("实验结束，正在生成对比表格...")

# 4. 展示结果
df_results = pd.DataFrame(results)

# 设置 pandas 显示选项以便查看完整内容
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)

print(df_results)

# 可选：保存到 Excel 方便截图提交
# df_results.to_excel("extraction_experiment_results.xlsx", index=False)