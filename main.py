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

# 引入免费的官方学术 API
try:
    from semanticscholar import SemanticScholar
except ImportError:
    print("[Error] 找不到 semanticscholar 库，请运行 pip install semanticscholar")
    exit()

# --- 1. 初始化配置 ---
load_dotenv()

def load_config():
    """读取 YAML 配置文件"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("[Error] 找不到 config.yaml 文件。")
        exit()

# --- 2. 初始化引擎 (封装为函数) ---
def init_services(api_key, base_url, model_name="gpt-4o-mini", sch_api_key=None):
    if not api_key:
        raise ValueError("[Error] API Key is missing!")
    
    llm = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=0.3)
    web_tool = TavilySearchResults(max_results=3)
    
    # 初始化 Semantic Scholar
    sch_engine = SemanticScholar(api_key=sch_api_key)
    
    return llm, web_tool, sch_engine

# --- 3. 定义数据结构 ---
class SchoolReport(BaseModel):
    school_name: str = Field(description="Name of the university (Keep English)")
    source: str = Field(description="Source of this entry")
    accept_det: str = Field(description="Yes/No/Mentioned")
    funding_policy: str = Field(description="Full funding policy summary")
    best_match_professor: str = Field(description="Professor name (Keep English)")
    research_fit_score: int = Field(description="0-100 score")
    match_reason: str = Field(description="Detailed reason for fit (Translate to target language)")
    red_flags: str = Field(description="Potential risks (Translate to target language) or 'None'")
    source_url: str = Field(description="Verification URL")

# --- 4. 定义 Prompts (封装为函数) ---
def get_prompts(language="English"):
    if language == "Chinese":
        recommender_template = """
        你是一个资深的CS博士留学顾问。
        用户背景: {profile}
        已排除学校: {manual_list}
        任务：补充推荐 {count} 所适合该背景的美国学校。
        要求：仅输出一个 JSON 学校英文名列表。例如: ["School A", "School B"]
        """
        
        analyzer_template = """
        你是一个博士申请侦察兵。请结合【网页搜索】和【学术搜索】的结果进行分析。
        
         **核心指令：请扮演一名专业的中文翻译。**
        除了【学校名】、【教授名】、【论文标题】、【会议名(如CVPR)】保留英文外，
        **其他所有描述性文字（包括匹配理由、奖学金政策、避坑预警）必须翻译成流畅的中文。**
        
        用户兴趣: {interest}
        目标学校: {school_name}

        【Web Search (行政/口碑)】:
        {web_context}

        【Semantic Scholar (学术论文)】:
        {academic_context}

        任务细节：
        1. **硬指标**: 确认 DET (多邻国) 和 全奖政策。
        2. **导师匹配**: 寻找最匹配的导师。如果论文发表在顶级会议(CVPR, NeurIPS等)，请加分。
        3. **匹配理由**: 必须用**中文**解释。
           -  正确: "该教授在视觉导航领域发表了多篇 CVPR 论文，与你的背景高度契合。"
           -  错误: "His research is about Visual Navigation."
        4. **避坑预警**: 检查是否有负面评价。如果有，用中文写出；如果没有，填 "无"。

        请严格输出 JSON 格式:
        {format_instructions}
        """
    else:
        recommender_template = """
        You are a Ph.D. admissions consultant.
        User Profile: {profile}
        Excluded: {manual_list}
        Task: Recommend {count} US universities fitting the profile.
        Output: JSON list of names only.
        """
        
        analyzer_template = """
        You are a Ph.D. scout. Analyze using search results.
        Output strictly in **English**.

        User Interest: {interest}
        School: {school_name}

        [Contexts]:
        {web_context}
        {academic_context}

        Task:
        1. Verify DET and Funding.
        2. Identify Best Match Professor (Bonus for top-tier venues like CVPR/NeurIPS).
        3. **Match Reason**: Explain the fit in English. Cite specific paper titles.
        4. **Red Flags**: Summarize negative sentiment in English; otherwise "None".

        Strict JSON Output:
        {format_instructions}
        """

    recommender_prompt = ChatPromptTemplate.from_template(recommender_template)
    analyzer_prompt = ChatPromptTemplate.from_template(analyzer_template)
    
    return recommender_prompt, analyzer_prompt

# --- 5. 核心功能函数 ---

def get_academic_papers(school_name, interest, sch_engine):
    """使用 Semantic Scholar 官方库搜索相关论文"""
    try:
        results = sch_engine.search_paper(
            query=f"{school_name} computer science {interest}",
            limit=4,
            fields=['title', 'abstract', 'venue', 'year', 'authors']
        )
        
        context = ""
        if not results:
            return "No specific papers found via Semantic Scholar."
            
        for i, paper in enumerate(results):
            title = paper.title if paper.title else "Unknown Title"
            venue = paper.venue if paper.venue else "Unknown Venue"
            year = paper.year if paper.year else "N/A"
            abstract = paper.abstract if paper.abstract else "No abstract available"
            
            authors_list = [author.name for author in paper.authors[:3]] if paper.authors else []
            authors = ", ".join(authors_list)
            
            context += f"[{i+1}] {title} ({venue}, {year})\nAuthors: {authors}\nAbstract: {abstract[:150]}...\n\n"
        
        return context
    except Exception as e:
        return f"Academic search error: {str(e)[:100]}"

def get_ai_recommendations(llm, recommender_prompt, profile, manual_list, count, language="English"):
    msg = "[Agent 1]: Generating recommendations..." if language != "Chinese" else "[Agent 1]: 正在生成推荐名单..."
    print(f"\n{msg}")
    chain = recommender_prompt | llm | StrOutputParser()
    try:
        result = chain.invoke({
            "profile": str(profile), 
            "manual_list": str(manual_list),
            "count": count
        })
        result = result.replace("```json", "").replace("```", "").strip()
        school_list = json.loads(result)
        print(f"    AI Suggestions: {school_list}")
        return school_list
    except:
        return []

def analyze_school(school_name, source_type, llm, analyzer_prompt, web_tool, sch_engine, interest):
    msg = f"Scouting: {school_name}"
    print(msg)
    
    try:
        # 关键修改 (方案一): 优化搜索词
        # 强制搜索 "Graduate Catalog" (目录) 和 "Handbook" (手册)
        # 这些通常是静态 PDF/纯文本，比花哨的官网更容易抓取 DET 分数
        web_query = f"{school_name} Computer Science PhD graduate catalog student handbook Duolingo score funding policy"
        
        web_results = web_tool.invoke(web_query)
        web_context = "\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in web_results])

        academic_context = get_academic_papers(school_name, interest, sch_engine)

        parser = JsonOutputParser(pydantic_object=SchoolReport)
        chain = analyzer_prompt | llm | parser
        
        result = chain.invoke({
            "school_name": school_name,
            "interest": interest,
            "web_context": web_context,
            "academic_context": academic_context,
            "format_instructions": parser.get_format_instructions()
        })
        
        result['source'] = source_type
        if not result.get('source_url'): result['source_url'] = "N/A"
            
        print(f"    {school_name} Done! Score: {result.get('research_fit_score')}")
        return result

    except Exception as e:
        print(f"    {school_name} Failed: {e}")
        return None

def clean_text_for_chinese(text):
    """简单的后处理，将常见英文关键词替换为中文"""
    if not isinstance(text, str): return text
    replacements = {
        "Yes": "是", "No": "否", "Mentioned": "提及",
        "Full funding guaranteed": "全额奖学金",
        "Fully Funded": "全额奖学金",
        "Not specified": "未明确",
        "None": "无", "Safe": "无风险",
        "Uncertain": "需人工核实", "Check Manually": "需人工核实"
    }
    for eng, chn in replacements.items():
        if text.lower() == eng.lower():
            return chn
        if eng in text: # 处理包含情况，如 "Uncertain (Check Manually)"
             text = text.replace(eng, chn)
    return text

def generate_html_report(df, language="English"):
    """生成 HTML 报告 (修复排版与列错位)"""
    if language == "Chinese":
        title, table_title = "PhD-Scout 战略分析报告", "详细数据表"
        # 定义表头顺序
        headers = ["学校名称", "来源", "契合度", "多邻国?", "全奖?", "推荐导师", "匹配理由", "避坑预警", "链接"]
        
        # 强制汉化部分字段
        for col in ['accept_det', 'funding_policy', 'red_flags']:
            df[col] = df[col].apply(clean_text_for_chinese)
    else:
        title, table_title = "PhD-Scout Strategy Report", "Detailed Data Table"
        headers = ["School", "Source", "Fit Score", "DET Accepted?", "Funding?", "Best Match Prof", "Match Reason", "Red Flags", "Link"]

    # 1. 关键修复：强制重排 DataFrame 的列顺序以匹配表头
    # 这一步解决了“数据错位”的问题
    correct_order = [
        'school_name', 
        'source', 
        'research_fit_score',  # 契合度 (Fit Score)
        'accept_det',          # 多邻国? (DET Accepted?)
        'funding_policy',      # 全奖? (Funding?)
        'best_match_professor',# 推荐导师 (Best Match Prof)
        'match_reason',        # 匹配理由 (Match Reason)
        'red_flags',           # 避坑预警 (Red Flags)
        'source_url'           # 链接 (Link)
    ]
    
    # 创建显示用的副本，并按正确顺序排列
    display_df = df[correct_order].copy()
    
    # 2. 链接处理
    display_df['source_url'] = display_df['source_url'].apply(lambda x: f'<a href="{x}" target="_blank">Link</a>' if x and x!="N/A" else "N/A")
    
    # 3. 分数高亮
    def format_score(s):
        try:
            val = int(s)
            return f'<span style="color:{"#28a745" if val>=80 else "#333"}; font-weight:bold">{val}</span>'
        except: return s
    display_df['research_fit_score'] = display_df['research_fit_score'].apply(format_score)
    
    # 4. 避坑预警高亮
    def format_flags(f):
        if f and f not in ["None", "无", "N/A", "None mentioned", "无风险"]:
            return f'<span style="color:#dc3545; font-weight:bold"> {f}</span>'
        return f'<span style="color:#28a745">Safe</span>'
    display_df['red_flags'] = display_df['red_flags'].apply(format_flags)

    # 5. 设置表头
    display_df.columns = headers

    # 生成表格HTML
    table_html = display_df.to_html(index=False, escape=False, border=0, classes="table-custom")

    # CSS 修复排版：增加 .table-wrapper 实现横向滚动
    html = f"""
    <!DOCTYPE html>
    <html lang="{language}">
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f4f6f9; }}
            .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            h1 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; color: #2c3e50; }}
            
            /* 表格容器：关键修复，允许横向滚动 */
            .table-wrapper {{ overflow-x: auto; margin-top: 20px; border-radius: 8px; border: 1px solid #eee; }}
            
            table {{ width: 100%; min-width: 1000px; border-collapse: collapse; font-size: 14px; }}
            th {{ background: #3498db; color: white; padding: 12px; text-align: left; white-space: nowrap; }}
            td {{ padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
            tr:hover {{ background: #f1f8ff; }}
            a {{ color: #3498db; text-decoration: none; }}
            
            /* 列宽建议 (非强制，允许浏览器调整) */
            th:nth-child(7) {{ min-width: 300px; }} /* 匹配理由给宽一点 */
            th:nth-child(8) {{ min-width: 150px; }} /* 避坑预警 */
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <p>Generated by PhD-Scout (Dual-Engine)</p>
            <h2>{table_title}</h2>
            <div class="table-wrapper">
                {table_html}
            </div>
        </div>
    </body>
    </html>
    """
    with open("phd_report.html", "w", encoding="utf-8") as f: f.write(html)
    return "phd_report.html"

# --- 6. 主程序 ---
if __name__ == "__main__":
    # 加载配置
    config = load_config()
    USER_PROFILE = config['profile']
    MANUAL_TARGETS = config['manual_targets']
    SETTINGS = config['settings']
    LANG = SETTINGS.get('report_language', 'English')
    
    # 获取环境变量
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    sch_api_key = os.getenv("SEMANTIC_SCHOLAR_KEY")

    # 初始化服务
    print(f"[Info] 初始化 Agent 模型: {model_name} (语言: {LANG})")
    llm, web_tool, sch_engine = init_services(api_key, base_url, model_name, sch_api_key)
    recommender_prompt, analyzer_prompt = get_prompts(LANG)

    # 汉化硬编码的 Source 标签
    src_manual = "手动目标" if LANG == "Chinese" else "Manual Target"
    src_ai = "AI 推荐" if LANG == "Chinese" else "AI Recommendation"

    final_list = [{"name": s, "source": src_manual} for s in MANUAL_TARGETS]
    
    # 获取 AI 推荐
    ai_schools = get_ai_recommendations(llm, recommender_prompt, USER_PROFILE, MANUAL_TARGETS, SETTINGS['recommendation_count'], LANG)
    for s in ai_schools: final_list.append({"name": s, "source": src_ai})
    
    msg = f"\n[Info] Parallel Scanning {len(final_list)} schools (Max Workers: 3)..." if LANG != "Chinese" else f"\n[Info] 正在并发扫描 {len(final_list)} 所学校 (最大线程: 3)..."
    print(msg)
    
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # 注意这里需要传递所有依赖
        future_to_school = {
            executor.submit(
                analyze_school, 
                item['name'], 
                item['source'], 
                llm, 
                analyzer_prompt, 
                web_tool, 
                sch_engine, 
                USER_PROFILE['research_interest']
            ): item for item in final_list
        }
        for future in concurrent.futures.as_completed(future_to_school):
            data = future.result()
            if data: results.append(data)
        
    if results:
        df = pd.DataFrame(results).sort_values(by=['research_fit_score'], ascending=False)
        df.to_csv("phd_strategy_report.csv", index=False)
        report_file = generate_html_report(df, language=LANG)
        print(f"\n[Success] Report: {report_file}")
        try: webbrowser.open(f'file://{os.path.realpath(report_file)}')
        except: pass
    else:
        print("\n[Error] No data.")