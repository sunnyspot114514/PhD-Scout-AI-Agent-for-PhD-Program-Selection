import os
import json
import yaml
import pandas as pd
import webbrowser
import concurrent.futures
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from difflib import SequenceMatcher

try:
    from semanticscholar import SemanticScholar
except ImportError:
    SemanticScholar = None
    print("[Warning] semanticscholar not installed. Academic paper search disabled.")


load_dotenv()

# --- 1. 配置加载 ---
def load_config():
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("[Error] 找不到 config.yaml 文件。")
        exit()

# --- 2. 服务初始化 ---
def init_services(api_key, base_url, model_name="gpt-4o-mini", sch_api_key=None):
    if not api_key: raise ValueError("[Error] API Key is missing!")
    llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=0.3)
    web_tool = TavilySearchResults(max_results=4) 
    
    # 2. 安全初始化
    sch_engine = None
    if SemanticScholar:
        try:
            sch_engine = SemanticScholar(api_key=sch_api_key)
        except Exception as e:
            print(f"[Warning] SemanticScholar init failed: {e}")
            
    return llm, web_tool, sch_engine

# --- 3. 数据结构 ---
class SchoolReport(BaseModel):
    school_name: str = Field(description="Name of the university")
    source: str = Field(description="Source of this entry")
    language_req: str = Field(description="Waiver Verdict AND Specific Score Requirements")
    funding_policy: str = Field(description="Details on Stipend, Tuition Waiver, and Health Insurance")
    best_match_professor: str = Field(description="Professor name or 'Not found'")
    research_fit_score: int = Field(description="0-100 score (Must be multiple of 5)")
    match_reason: str = Field(description="Detailed reason for fit")
    red_flags: str = Field(description="Potential risks formatted as numbered list")
    source_url: str = Field(description="Verification URL")

# --- 4. 辅助函数 ---
def check_is_alumni(school_name, highest_school):
    if not highest_school or len(highest_school) < 3: return False
    ignore_words = ["university", "of", "college", "institute", "the"]
    
    def clean(s):
        words = s.lower().split()
        return " ".join([w for w in words if w not in ignore_words])

    s1 = clean(school_name)
    s2 = clean(highest_school)
    
    if s1 in s2 or s2 in s1: return True
    ratio = SequenceMatcher(None, s1, s2).ratio()
    return ratio > 0.85

def ensure_english_term(llm, text):
    if not text or len(text) < 2: return ""
    if not re.search(r'[\u4e00-\u9fa5]', text):
        return text 
    print(f"[Translator] Translating '{text}' to English...")
    prompt = ChatPromptTemplate.from_template(
        "Translate the following academic term/major into English. Output ONLY the English term. No explanations. Term: {text}"
    )
    chain = prompt | llm | StrOutputParser()
    try:
        return chain.invoke({"text": text}).strip()
    except:
        return text

# --- 5. Prompts (包含去重修复 + 阶梯打分逻辑) ---
def get_prompts(language="English", major="Interdisciplinary", target_countries=None, strategy="Balanced"):
    if target_countries is None: target_countries = ["Global"]
    
    # 策略描述
    if strategy == "Top Tier (冲刺名校)":
        strat_hint = "Focus only on Top 30 global universities."
    elif strategy == "High Match / Hidden Gems (高匹配/潜力股)":
        strat_hint = f"Ignore general rankings. Focus on strong {major} departments and hidden gems."
    elif strategy == "Safety / Safe Bets (保底/稳妥)":
        strat_hint = "Focus on schools with high acceptance rates and guaranteed funding."
    else:
        strat_hint = "Balance between reputation and research fit."

    # --- Recommender Prompt ---
    if language == "Chinese":
        recommender_template = f"""
        你是一位资深的 {major} 博士申请顾问。
        任务：基于用户背景，推荐 {{count}} 所 **新的**、**不在手动列表中的** 适合申请的大学。
        
        【用户背景】: {{profile}}
        【手动目标】: {{manual_list}}
        【策略】: {strategy} ({strat_hint})
        
        要求：
        1. **严禁推荐** 【手动目标】中已经列出的学校。必须推荐全新的学校。
        2. 仅输出一个 JSON 列表，例如 ["School A", "School B"]。
        3. 学校名称 **必须保留英文原名**。
        4. 不要输出 Markdown 格式。
        """
    else:
        recommender_template = f"""
        You are a Senior {major} Ph.D. Consultant.
        Task: Recommend {{count}} **NEW** universities based on the profile.
        
        [Profile]: {{profile}}
        [Manual Targets]: {{manual_list}}
        [Strategy]: {strategy} ({strat_hint})
        
        Requirements:
        1. Do **NOT** recommend any school listed in [Manual Targets]. Provide strictly new suggestions.
        2. Output strictly a JSON list of strings: ["School A", "School B"].
        3. Keep school names in English.
        4. No Markdown code blocks.
        """

    # --- Analyzer Prompt ---
    if language == "Chinese":
        analyzer_template = f"""
        你是一个学术情报分析员。你的任务是根据搜索到的英文信息，生成一份 **全中文** 的分析报告。
        
        【分析对象】: {{school_name}}
        【搜索结果】: {{web_context}}
        【论文数据】: {{academic_context}}
        【用户背景】: 毕业于 **{{highest_school}}** (是否校友: {{is_alumni_str}})

        请严格按照以下步骤思考并填写字段：
        1. **语言判定**: 寻找 {{english_test}} 要求。
        2. **资金**: 总结 Stipend, Tuition Waiver 信息。
        3. **导师**: 寻找与 "{{interest}}" 匹配的教授。
        4. **避坑**: 寻找潜在风险。
        
        5. **打分逻辑 (Research Fit Score)**:
           - 必须是 **5的倍数** (如 75, 80, 85)。
           - **校友加成**: 如果 (是否校友: True)，这是一个巨大的录取优势。**必须在原有匹配分基础上额外 +5 到 10 分**（总分不超过100）。
           - **90-100分**: 完美匹配 (方向一致 + 全奖 + 导师活跃) 或 (强匹配 + 校友身份)。
           - **80-85分**: 强匹配 (方向一致 + 资金可能) 或 (一般匹配 + 校友身份)。
           - **70-75分**: 一般匹配 (方向相关但非核心，资金/语言不明确)。
           - **< 65分**: 不匹配 (方向不对口，或有严重Red Flags)。
           
        6. **匹配理由 (Match Reason)**:
           - **如果 (是否校友: True)**，在理由开头加上 "[Alumni Edge]"。
           - **否则 (是否校友: False)**，**不要**提及校友身份，只基于科研、课程、资金等方面描述匹配度。
        
        请输出符合以下 JSON 格式的数据:
        {{format_instructions}}
        """
    else:
        analyzer_template = f"""
        You are an Academic Scout. Analyze the following school data.
        
        Target: {{school_name}}
        Context: {{web_context}}
        Paper Data: {{academic_context}}
        User Info: Graduated from {{highest_school}} (Alumni: {{is_alumni_str}})

        Instructions:
        1. **Language**: Output in ENGLISH.
        2. **Scoring Logic (Crucial)**:
           - Score MUST be a **multiple of 5**.
           - **ALUMNI BONUS**: If (Alumni: True), you **MUST boost the score by 5-10 points**.
           - **Tier 1 (90-100)**: Perfect Match OR (Strong Match + Alumni).
           - **Tier 2 (80-85)**: Strong Match OR (Moderate Match + Alumni).
           - **Tier 3 (70-75)**: Moderate Match.
           - **Tier 4 (< 65)**: Low Match.
        
        3. **Match Reason**:
           - **If (Alumni: True)**, start the match_reason with "[Alumni Edge]".
           - **If (Alumni: False)**, **DO NOT mention** the alumni status. Focus solely on research, program, funding fit, etc.
        
        Output strictly in JSON:
        {{format_instructions}}
        """

    recommender_prompt = ChatPromptTemplate.from_template(recommender_template)
    analyzer_prompt = ChatPromptTemplate.from_template(analyzer_template)
    return recommender_prompt, analyzer_prompt

# --- 6. 通用去重 ---
def deduplicate_school_list(llm, raw_list):
    print(f"\n[System] 正在进行去重 (输入: {len(raw_list)})...")
    unique_schools = {}
    
    def get_key(name):
        clean = name.lower().strip()
        clean = re.sub(r'[^\w\s]', '', clean)
        clean = clean.replace("univ ", "university ").replace("inst ", "institute ")
        clean = clean.replace("tech ", "technology ")
        clean = " ".join(clean.split())
        return clean

    for item in raw_list:
        if "AI" not in item['source']:
            key = get_key(item['name'])
            unique_schools[key] = item
            
    ai_added = 0
    for item in raw_list:
        if "AI" in item['source']:
            key = get_key(item['name'])
            if key not in unique_schools:
                unique_schools[key] = item
                ai_added += 1
    
    final = list(unique_schools.values())
    return final

# --- 7. 核心功能 ---
def get_academic_papers(school_name, interest_en, sch_engine, major_en="Computer Science"):
    #  安全调用检查
    if not sch_engine:
        return "Academic search disabled (Library not loaded)."

    try:
        clean_major = major_en.replace("PhD in ", "").replace("Ph.D. in ", "").replace("/", " ").strip()
        short_major = " ".join(clean_major.split()[:3]) 
        
        query = f"{school_name} {short_major} {interest_en}"
        results = sch_engine.search_paper(query=query, limit=3, fields=['title', 'abstract', 'venue', 'year', 'authors'])
        
        context = ""
        if not results: return "No specific papers found."
        for i, paper in enumerate(results):
            authors = ", ".join([a.name for a in paper.authors[:3]]) if paper.authors else ""
            context += f"[{i+1}] {paper.title} ({paper.year})\nAbstract: {(paper.abstract or '')[:150]}...\n"
        return context
    except Exception as e: return f"Academic search error: {str(e)[:100]}"

def get_ai_recommendations(llm, recommender_prompt, profile, manual_list, count, language="English"):
    print(f"\n[Agent 1] Generating recommendations...")
    chain = recommender_prompt | llm | StrOutputParser()
    try:
        h_school = profile.get('highest_school', 'Unknown') if isinstance(profile, dict) else "Unknown"
        raw_content = chain.invoke({
            "profile": str(profile), 
            "manual_list": str(manual_list), 
            "highest_school": h_school, 
            "count": count
        })
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\[.*\]', clean_content, re.DOTALL)
        return json.loads(match.group()) if match else []
    except Exception:
        return []

def analyze_school(school_name, source_type, llm, analyzer_prompt, web_tool, sch_engine, 
                   interest, major, highest_school, current_degree, english_test, search_keywords):
    msg = f"Scouting: {school_name}"
    print(msg)
    try:
        search_major_en = ensure_english_term(llm, major)
        raw_keywords = search_keywords if search_keywords else interest
        search_keywords_en = ensure_english_term(llm, raw_keywords)
        
        user_test = "TOEFL IELTS"
        if english_test:
            if "Duolingo" in english_test or "DET" in english_test: user_test = "Duolingo minimum score"
            elif "IELTS" in english_test: user_test = "IELTS minimum score"
            elif "TOEFL" in english_test: user_test = "TOEFL minimum score"
        
        web_query = (
            f"{school_name} {search_major_en} PhD admission requirements "
            f"language waiver {user_test} "
            f"PhD student funding package stipend amount tuition waiver health insurance assistantship handbook"
        )
        
        web_results = web_tool.invoke(web_query)
        web_context = "\n".join([f"Src: {res['url']}\nTxt: {res['content']}" for res in web_results])
        
        academic_context = get_academic_papers(school_name, search_keywords_en, sch_engine, search_major_en)

        is_alumni = check_is_alumni(school_name, highest_school)
        is_alumni_str = "True" if is_alumni else "False"

        parser = JsonOutputParser(pydantic_object=SchoolReport)
        chain = analyzer_prompt | llm | parser
        
        result = chain.invoke({
            "school_name": school_name, "interest": interest, 
            "web_context": web_context, "academic_context": academic_context,
            "highest_school": highest_school, "current_degree": current_degree, 
            "english_test": english_test,
            "is_alumni_str": is_alumni_str,
            "format_instructions": parser.get_format_instructions()
        })
        
        result['source'] = source_type
        if not result.get('source_url'): result['source_url'] = "N/A"
        return result
    except Exception as e:
        print(f"    {school_name} Failed: {e}")
        return None

# --- HTML Report Generators ---
def clean_text_for_chinese(text):
    if not isinstance(text, str): return text
    if "Information not found" in text: return "需人工核实"
    return text

def generate_html_report(df, language="English"):
    if language == "Chinese":
        title, table_title = "PhD-Scout 全球战略分析报告", "详细数据表"
        headers = ["学校名称", "来源", "契合度", "语言要求", "资金政策 (官方)", "导师", "匹配理由", "避坑 (Red Flags)", "链接"]
    else:
        title, table_title = "PhD-Scout Strategy Report", "Data Table"
        headers = ["School", "Source", "Score", "Language Req", "Funding Policy", "Professors", "Match Reason", "Red Flags", "Link"]

    correct_order = ['school_name', 'source', 'research_fit_score', 'language_req', 'funding_policy', 'best_match_professor', 'match_reason', 'red_flags', 'source_url']
    for col in correct_order: 
        if col not in df.columns: df[col] = "N/A"

    display_df = df[correct_order].copy()
    
    display_df['source_url'] = display_df['source_url'].apply(lambda x: f'<a href="{x}" target="_blank">🔗</a>' if x and x!="N/A" else "-")
    
    display_df['research_fit_score'] = display_df['research_fit_score'].apply(lambda s: f'<span style="color:{"#28a745" if str(s).isdigit() and int(s)>=80 else "#333"}; font-weight:bold; font-size:1.1em">{s}</span>')
    
    def format_red_flags(text):
        if not isinstance(text, str): return text
        # 定义安全词 (不区分大小写，增加 N/A 等)
        safe_keywords = ["None", "无", "无风险", "Safe", "None found", "N/A", "Not found"]
        if any(k.lower() == text.strip().lower() for k in safe_keywords):
            return '<span style="color:#28a745; font-weight:bold">Safe</span>'
        # 1. 预处理：将所有原始换行符替换为空格，防止出现双重换行
        text = text.replace('\n', ' ')
        text = re.sub(r'(?<!^)\s*(\d+\.)', r'<br>\1', text)
        
        return f'<span style="color:#dc3545; font-weight:bold; font-size:0.95em">{text}</span>'

    display_df['red_flags'] = display_df['red_flags'].apply(format_red_flags)
    
    def highlight_funding(text):
        if any(k in text for k in ["Full", "Fully", "全奖", "全额"]):
            return f'<span style="color:#0056b3; font-weight:bold">{text}</span>'
        return text
    display_df['funding_policy'] = display_df['funding_policy'].apply(highlight_funding)

    display_df.columns = headers
    table_html = display_df.to_html(index=False, escape=False, border=0, classes="table-custom")
    
    html = f"""<!DOCTYPE html><html lang="{language}"><head><meta charset="UTF-8"><title>{title}</title>
    <style>
        body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"Microsoft YaHei",sans-serif;max-width:98%;margin:0 auto;padding:20px;background:#f4f6f9}}
        .container{{background:white;padding:20px;border-radius:10px;box-shadow:0 2px 5px rgba(0,0,0,0.1)}}
        h1{{border-bottom:2px solid #eee;padding-bottom:10px;color:#2c3e50; font-size: 1.5rem}}
        table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 13px; }}
        th {{ background:#3498db; color:white; padding:10px 5px; text-align:left; overflow:hidden; }}
        td {{ padding:8px 5px; border-bottom:1px solid #eee; vertical-align:top; word-wrap: break-word; color: #333; }}
        tr:hover {{ background:#f1f8ff }}
        a {{ text-decoration: none; font-weight: bold; font-size: 1.2em; }}
        th:nth-child(1) {{ width: 10%; }}
        th:nth-child(2) {{ width: 5%; }}
        th:nth-child(3) {{ width: 4%; }}
        th:nth-child(4) {{ width: 12%; }}
        th:nth-child(5) {{ width: 14%; }}
        th:nth-child(6) {{ width: 10%; }}
        th:nth-child(7) {{ width: 20%; }}
        th:nth-child(8) {{ width: 20%; }}
        th:nth-child(9) {{ width: 5%; }}
    </style>
    </head><body><div class="container"><h1>{title}</h1><h2>{table_title}</h2>{table_html}</div></body></html>"""
    
    with open("phd_report.html", "w", encoding="utf-8") as f: f.write(html)
    return "phd_report.html"

if __name__ == "__main__":
    print("Please use 'streamlit run app.py'")