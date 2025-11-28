import os
import json
import yaml
import pandas as pd
import webbrowser
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field

# --- 1. 初始化配置 ---
load_dotenv()

def load_config():
    """读取 YAML 配置文件"""
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("[错误]: 找不到 config.yaml 文件。请确保它在根目录下。")
        exit()

config = load_config()
USER_PROFILE = config['profile']
MANUAL_TARGETS = config['manual_targets']
SETTINGS = config['settings']
LANG = SETTINGS.get('report_language', 'English')  # 获取语言设置

# --- 2. 初始化 LLM 和工具 ---
api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")
model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

if not api_key:
    raise ValueError("[警告] 请在 .env 文件中设置 LLM_API_KEY！")

print(f"[Info] 初始化 Agent 模型: {model_name}")
print(f"[Info] 报告语言设置为: {LANG}")

llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.3
)

search_tool = TavilySearchResults(max_results=SETTINGS['max_search_results'])

# --- 3. 定义数据结构 ---
class SchoolReport(BaseModel):
    school_name: str = Field(description="Name of the university")
    source: str = Field(description="'Manual Target' or 'AI Recommendation'")
    accept_det: str = Field(description="Yes/No/Mentioned")
    funding_policy: str = Field(description="Full funding guaranteed?")
    best_match_professor: str = Field(description="Professor name")
    research_fit_score: int = Field(description="0-100 score")
    match_reason: str = Field(description="Reason for fit")
    source_url: str = Field(description="Verification URL")

# --- 4. 动态定义 Prompts (关键修改) ---

if LANG == "Chinese":
    # === 中文提示词 ===
    recommender_template = """
    你是一个资深的CS博士留学顾问。
    用户背景: {profile}
    已排除学校: {manual_list}

    任务：补充推荐 {count} 所适合该背景（特别是GPA和科研方向）的美国学校。
    要求：仅输出一个 JSON 学校英文名列表。例如: ["School A", "School B"]
    """
    
    analyzer_template = """
    你是一个博士申请侦察兵。请完全使用**中文**进行分析和输出（除了人名和专有名词）。
    用户背景/兴趣: {interest}
    目标学校: {school_name}

    搜索结果上下文:
    {context}

    任务:
    1. 确认该校CS PhD是否接受 Duolingo (DET)。
    2. 确认 Funding 政策。
    3. 寻找与用户方向 ({interest}) 匹配的导师并打分 (0-100)。
    4. **match_reason** 字段必须用**中文**详细解释为什么匹配。

    请严格输出 JSON 格式:
    {format_instructions}
    """

else:
    # === English Prompts ===
    recommender_template = """
    You are a senior Ph.D. admissions consultant.
    User Profile: {profile}
    Excluded Schools: {manual_list}

    Task: Recommend {count} US universities that fit the profile (considering GPA and research match).
    Requirement: Output ONLY a JSON list of school names. E.g. ["School A", "School B"]
    """
    
    analyzer_template = """
    You are a Ph.D. application scout. Please analyze and output **Strictly in English**.
    User Interest: {interest}
    School: {school_name}

    Search Context:
    {context}

    Task:
    1. Check if Duolingo (DET) is accepted.
    2. Check for Full Funding policies.
    3. Find the best matching professor for the user's interest and assign a fit score (0-100).
    4. The **match_reason** field MUST be written in **English**.

    Strict JSON Output:
    {format_instructions}
    """

# 生成 Prompt 对象
recommender_prompt = ChatPromptTemplate.from_template(recommender_template)
analyzer_prompt = ChatPromptTemplate.from_template(analyzer_template)

# --- 5. 核心功能函数 ---

def get_ai_recommendations():
    """调用 AI 获取推荐学校列表"""
    msg = "[Agent 1]: Generating recommendations..." if LANG != "Chinese" else "[Agent 1]: 正在根据背景生成推荐名单..."
    print(f"\n{msg}")
    
    chain = recommender_prompt | llm | StrOutputParser()
    try:
        result = chain.invoke({
            "profile": str(USER_PROFILE), 
            "manual_list": str(MANUAL_TARGETS),
            "count": SETTINGS['recommendation_count']
        })
        result = result.replace("```json", "").replace("```", "").strip()
        school_list = json.loads(result)
        
        msg_done = f"[AI Suggested]: {school_list}" if LANG != "Chinese" else f"[AI 建议关注]: {school_list}"
        print(msg_done)
        return school_list
    except Exception as e:
        print(f"[Error]: {e}")
        return []

def analyze_school(school_name, source_type):
    """调用 Tavily 和 AI 分析特定学校"""
    msg = f"[Agent 2]: Scouting {school_name} ({source_type})..." if LANG != "Chinese" else f"[Agent 2]: 正在侦察 {school_name} ({source_type})..."
    print(msg)
    
    try:
        # 搜索查询保持英文以提高准确率
        query = f"{school_name} Computer Science PhD admission requirements Duolingo funding faculty research interests {USER_PROFILE['research_interest']}"
        search_results = search_tool.invoke(query)
        
        context_text = "\n".join([f"Source: {res['url']}\nContent: {res['content']}" for res in search_results])

        parser = JsonOutputParser(pydantic_object=SchoolReport)
        chain = analyzer_prompt | llm | parser
        
        result = chain.invoke({
            "school_name": school_name,
            "interest": USER_PROFILE['research_interest'],
            "context": context_text,
            "format_instructions": parser.get_format_instructions()
        })
        
        result['source'] = source_type
        if not result.get('source_url'): 
            result['source_url'] = "N/A"
            
        print(f"   [Done] Score: {result.get('research_fit_score')} - Prof: {result.get('best_match_professor')}")
        return result

    except Exception as e:
        print(f"   [Failed]: {e}")
        return {
            "school_name": school_name, "source": source_type,
            "accept_det": "Error", "funding_policy": "Error",
            "best_match_professor": "Error", "research_fit_score": 0,
            "match_reason": str(e), "source_url": "N/A"
        }

def generate_html_report(df, language="English"):
    """生成静态 HTML 报告"""
    
    if language == "Chinese":
        title = "PhD-Scout 战略分析报告"
        subtitle = f"生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}<br>目标方向: {USER_PROFILE['research_interest']}"
        headers = ["学校名称", "来源", "契合度", "多邻国?", "全奖?", "推荐导师", "匹配理由", "验证链接"]
        summary_template = "共扫描了 <b>{total}</b> 所学校。其中 <b>{high_fit}</b> 所学校的科研契合度超过 80 分。建议优先关注这些项目。"
        table_title = "详细数据表"
    else:
        title = "PhD-Scout Strategy Report"
        subtitle = f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}<br>Target Area: {USER_PROFILE['research_interest']}"
        headers = ["School", "Source", "Fit Score", "DET Accepted?", "Funding?", "Best Match Prof", "Match Reason", "Source URL"]
        summary_template = "Scanned a total of <b>{total}</b> schools. Found <b>{high_fit}</b> schools with a research fit score over 80. These should be your top priority."
        table_title = "Detailed Data Table"

    display_df = df.copy()
    
    def format_link(url):
        if url and url != "N/A":
            return f'<a href="{url}" target="_blank">Link</a>'
        return "N/A"
    
    display_df['source_url'] = display_df['source_url'].apply(format_link)
    
    def format_score(score):
        try:
            s = int(score)
            color = "#28a745" if s >= 80 else "#333" if s >= 60 else "#dc3545"
            weight = "bold" if s >= 80 else "normal"
            return f'<span style="color:{color}; font-weight:{weight}">{s}</span>'
        except:
            return score
        
    display_df['research_fit_score'] = display_df['research_fit_score'].apply(format_score)
    display_df.columns = headers

    high_fit_count = len(df[df['research_fit_score'] >= 80])
    summary_text = summary_template.format(total=len(df), high_fit=high_fit_count)
    table_html = display_df.to_html(index=False, escape=False, border=0, classes="table-custom")

    html_template = f"""
    <!DOCTYPE html>
    <html lang="{language}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; background-color: #f8f9fa; }}
            .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eaeaea; padding-bottom: 10px; margin-bottom: 5px; }}
            .summary {{ background-color: #e8f5e9; padding: 15px; border-left: 5px solid #4caf50; border-radius: 4px; margin: 20px 0; }}
            .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background-color: #007bff; color: white; padding: 12px; text-align: left; position: sticky; top: 0; }}
            td {{ padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
            tr:hover {{ background-color: #f1f8ff; }}
            a {{ color: #007bff; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
            .table-wrapper {{ overflow-x: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{title}</h1>
            <div class="meta">{subtitle}</div>
            <div class="summary">{summary_text}</div>
            <h2>{table_title}</h2>
            <div class="table-wrapper">{table_html}</div>
        </div>
    </body>
    </html>
    """

    filename = "phd_report.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    return filename

# --- 6. 主程序入口 ---
if __name__ == "__main__":
    final_list = [{"name": s, "source": "Manual Target"} for s in MANUAL_TARGETS]
    
    ai_schools = get_ai_recommendations()
    for s in ai_schools:
        final_list.append({"name": s, "source": "AI Recommendation"})
    
    msg = f"\n[Info] Targets Locked! Scanning {len(final_list)} schools..." if LANG != "Chinese" else f"\n[Info] 目标锁定！即将扫描 {len(final_list)} 所学校..."
    print(msg)
    
    results = []
    for item in final_list:
        data = analyze_school(item['name'], item['source'])
        if data:
            results.append(data)
        
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(by=['research_fit_score'], ascending=False)
        df.to_csv("phd_strategy_report.csv", index=False)
        
        html_filename = generate_html_report(df, language=LANG)
        
        print(f"[Success] Report Generated: {html_filename}")
        try:
            file_path = os.path.realpath(html_filename)
            webbrowser.open(f'file://{file_path}')
        except:
            print("Please open the HTML file manually.")
    else:
        print("[Error] No data generated.")