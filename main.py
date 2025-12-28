import os
import json
import yaml
import time
import pandas as pd
import webbrowser
import concurrent.futures
import re
from typing import Union
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from pydantic import BaseModel, Field
from difflib import SequenceMatcher
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

# 导入日志系统
from logger import logger

try:
    from semanticscholar import SemanticScholar
except ImportError:
    SemanticScholar = None
    logger.warning("semanticscholar not installed. Academic paper search disabled.")


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
            logger.info("Semantic Scholar 初始化成功")
        except Exception as e:
            logger.warning(f"Semantic Scholar 初始化失败: {e}")
            print(f"[Warning] SemanticScholar init failed: {e}")  # 保持原有输出
            
    return llm, web_tool, sch_engine

# --- 3. 数据结构 ---
class SchoolReport(BaseModel):
    school_name: str = Field(description="Name of the university")
    source: str = Field(description="Source of this entry")
    language_req: str = Field(description="Waiver Verdict AND Specific Score Requirements")
    funding_policy: str = Field(description="Details on Stipend, Tuition Waiver, and Health Insurance")
    best_match_professor: str = Field(description="Professor name or 'Not found'")
    research_fit_score: Union[int, str] = Field(description="0-100 score (Must be multiple of 5)") 
    match_reason: str = Field(description="Detailed reason for fit")
    red_flags: str = Field(description="Potential risks formatted as numbered list")
    source_url: str = Field(description="Verification URL")
    application_deadline: str = Field(description="Application deadline (e.g., 'Dec 15, 2025' or 'Rolling')")
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
    logger.debug(f"Translating '{text}' to English...")
    print(f"[Translator] Translating '{text}' to English...")  # 保持原有输出
    prompt = ChatPromptTemplate.from_template(
        "Translate the following academic term/major into English. Output ONLY the English term. No explanations. Term: {text}"
    )
    chain = prompt | llm | StrOutputParser()
    try:
        result = chain.invoke({"text": text}).strip()
        logger.debug(f"Translation result: {result}")
        return result
    except Exception as e:
        logger.error(f"Translation failed for '{text}': {e}")
        return text

# --- 5. Prompts (包含去重修复 + 阶梯打分逻辑) ---
def get_prompts(language="English", major="Interdisciplinary", target_countries=None, strategy="Balanced"):
    # 地理位置处理
    if not target_countries or "Global" in target_countries:
        geo_str = "Global (Any country)" if language == "English" else "全球 (不限国家)"
    else:
        geo_list_str = ", ".join(target_countries)
        geo_str = f"Only within: {geo_list_str}" if language == "English" else f"仅限以下地区: {geo_list_str}"
    
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
        任务：基于用户背景，在**指定地理范围内**推荐 {{count}} 所 **新的**、**不在手动列表中的** 适合申请的大学。
        
        【限制区域】: {geo_str}
        【用户背景】: {{profile}}
        【手动目标】: {{manual_list}}
        【策略】: {strategy} ({strat_hint})
        
        要求：
        1. **严禁推荐** 【手动目标】中已经列出的学校。必须推荐全新的学校。
        2. 仅输出一个 JSON 列表，例如 ["School A", "School B"]。
        3. 学校名称 **必须保留英文原名**。
        4. 不要输出 Markdown 格式。
        5. **必须严格遵守【限制区域】**。如果限制了国家，绝对不要推荐其他国家的学校。
        """
    else:
        recommender_template = f"""
        You are a Senior {major} Ph.D. Consultant.
        Task: Based on the user's profile, recommend {{count}} suitable universities to apply to within the specified geographic range.
        
        [Profile]: {{profile}}
        [Manual Targets]: {{manual_list}}
        [Strategy]: {strategy} ({strat_hint})
        
        Requirements:
        1. Do **NOT** recommend any school listed in [Manual Targets]. Provide strictly new suggestions.
        2. Output strictly a JSON list of strings: ["School A", "School B"].
        3. Keep school names in English.
        4. No Markdown code blocks.
        5. **STRICTLY follow the [Target Region]**.
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
        4. **避坑**:
           - 寻找潜在风险（如：资金不保证、录取率极低、项目缩招等）。
           - **必须包含申请截止日期**，格式: "Deadline: Dec 15, 2025" 或 "Deadline: Rolling"。
           - 如果截止日期已过或临近（30天内），标记为风险。
        
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
        1. **Language Requirements**: Find {{english_test}} requirements. Check if waiver is possible.
        2. **Funding**: Summarize Stipend, Tuition Waiver, and Health Insurance details.
        3. **Faculty Match**: Find professors whose research aligns with "{{interest}}".
        4. **Red Flags**:
        - Include potential risks (e.g., no guaranteed funding, low acceptance rate).
        - **MUST include application deadline** in format: "Deadline: Dec 15, 2025" or "Deadline: Rolling".
        - If deadline has passed or is within 30 days, mark as a risk.

        5. **Scoring Logic (Crucial)**:
        - Score MUST be a **multiple of 5**.
        - **ALUMNI BONUS**: If (Alumni: True), you **MUST boost the score by 5-10 points**.
        - **Tier 1 (90-100)**: Perfect Match (research fit + full funding + active advisor) OR (Strong Match + Alumni).
        - **Tier 2 (80-85)**: Strong Match (research fit + possible funding) OR (Moderate Match + Alumni).
        - **Tier 3 (70-75)**: Moderate Match (related but not core, unclear funding/language).
        - **Tier 4 (< 65)**: Low Match (misaligned research or serious Red Flags).

        6. **Match Reason**:
        - **If (Alumni: True)**, start the match_reason with "[Alumni Edge]".
        - **If (Alumni: False)**, **DO NOT mention** the alumni status. Focus solely on research, program, funding fit, etc.

        Output strictly in JSON:
        {{format_instructions}}
        """

    recommender_prompt = ChatPromptTemplate.from_template(recommender_template)
    analyzer_prompt = ChatPromptTemplate.from_template(analyzer_template)
    return recommender_prompt, analyzer_prompt

# --- 6. 通用去重  ---
def deduplicate_school_list(llm, raw_list):
    logger.info(f"开始去重处理: 输入 {len(raw_list)} 条记录")
    print(f"\n[System] 正在进行智能去重 (输入: {len(raw_list)})...")
    
    # === 1. 名称标准化 (关键修复) ===
    normalized_list = []
    
    # 定义 LLM 翻译链
    norm_prompt = ChatPromptTemplate.from_template(
        "What is the official English name of the university '{name}'? "
        "Output ONLY the full English name. No acronyms, no explanations."
    )
    norm_chain = norm_prompt | llm | StrOutputParser()

    # 判断是否需要标准化的辅助函数
    def needs_normalization(name):
        n = str(name).strip()
        # 1. 如果包含中文，必须翻译！(这是解决你问题的关键)
        if re.search(r'[\u4e00-\u9fa5]', n):
            return True
        # 2. 如果是简短的英文 (缩写)，需要展开
        # 例如 "SUSS" (4 chars), "MIT" (3 chars)
        if len(n) < 15 and re.match(r'^[A-Za-z0-9\s\(\)\.]+$', n):
            return True
        return False

    print("[System] 正在标准化手动输入的学校名称...")
    
    for item in raw_list:
        # 复制对象，防止修改原数据
        entry = item.copy() if isinstance(item, dict) else {'name': item, 'source': 'AI Recommendation'}
        if 'name' not in entry and 'school_name' in entry:
            entry['name'] = entry['school_name']

        name = entry['name']
        
        # 只处理“手动目标”，AI 推荐的通常已经是标准英文
        if "AI" not in entry.get('source', '') and needs_normalization(name):
            try:
                print(f"    [Trans] 正在翻译/标准化: {name} ...")
                # 调用 LLM
                full_name = norm_chain.invoke({"name": name}).strip()
                # 清洗一下 LLM 可能返回的引号
                full_name = full_name.replace('"', '').replace("'", "").replace(".", "")
                
                print(f"    结果: {full_name}")
                entry['name'] = full_name # 更新为英文名
            except Exception as e:
                logger.error(f"标准化失败 {name}: {e}")
                # 失败了也没办法，只能保留原名
        
        normalized_list.append(entry)

    # === 2. 定义清洗函数 (保持之前的核弹级清洗) ===
    def clean_name_for_compare(name):
        if not name: return ""
        n = str(name).lower()
        # 去除括号
        n = re.sub(r'[\(\[\{（【].*?[\)\]\}）】]', '', n)
        # 去除标点
        n = re.sub(r'[^\w\u4e00-\u9fa5]', '', n)
        # 缩写
        n = n.replace("technological", "tech").replace("technology", "tech")
        # 去除通用词
        for w in ["university", "univ", "college", "institute", "inst", "of", "the", "and", "&"]:
            n = n.replace(w, "")
        return n.strip()

    # === 3. 执行去重 ===
    # 排序：手动在前，AI 在后
    normalized_list.sort(key=lambda x: 0 if "AI" not in x.get('source', '') else 1)

    unique_list = []
    for current in normalized_list:
        is_duplicate = False
        curr_clean = clean_name_for_compare(current['name'])
        
        for existing in unique_list:
            exist_clean = clean_name_for_compare(existing['name'])
            
            # A: 完全相等
            if curr_clean == exist_clean:
                is_duplicate = True
                break
            # B: 相互包含 (防误判)
            if len(curr_clean) > 4 and len(exist_clean) > 4:
                if curr_clean in exist_clean or exist_clean in curr_clean:
                    is_duplicate = True
                    break
            # C: 相似度
            ratio = SequenceMatcher(None, curr_clean, exist_clean).ratio()
            if ratio > 0.82: 
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_list.append(current)
        else:
            logger.debug(f"剔除重复项: {current['name']}")
            print(f"[Dedup] 剔除重复项: {current['name']}")

    print(f"[System] 去重完成。保留: {len(unique_list)} (原始: {len(raw_list)})")
    return unique_list

# --- 7. 核心功能 ---
def get_academic_papers(school_name, interest_en, sch_engine, major_en="Computer Science"):
    #  安全调用检查
    if not sch_engine:
        logger.debug("Semantic Scholar 引擎未初始化，跳过学术论文搜索")
        return "Academic search disabled (Library not loaded)."

    try:
        clean_major = major_en.replace("PhD in ", "").replace("Ph.D. in ", "").replace("/", " ").strip()
        short_major = " ".join(clean_major.split()[:3]) 
        
        query = f"{school_name} {short_major} {interest_en}"
        logger.debug(f"学术论文搜索查询: {query}")
        
        # 设置超时：最多等待 10 秒
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                sch_engine.search_paper, 
                query=query, 
                limit=3, 
                fields=['title', 'abstract', 'venue', 'year', 'authors']
            )
            try:
                results = future.result(timeout=10)  # 10秒超时
            except concurrent.futures.TimeoutError:
                logger.warning(f"Semantic Scholar 搜索超时 (10s): {school_name}")
                return "Academic search timeout."
        
        context = ""
        if not results: 
            logger.debug(f"未找到 {school_name} 的相关论文")
            return "No specific papers found."
        for i, paper in enumerate(results):
            authors = ", ".join([a.name for a in paper.authors[:3]]) if paper.authors else ""
            context += f"[{i+1}] {paper.title} ({paper.year})\nAbstract: {(paper.abstract or '')[:150]}...\n"
        logger.debug(f"找到 {len(results)} 篇相关论文")
        return context
    except Exception as e: 
        logger.error(f"学术论文搜索失败: {str(e)[:100]}")
        return f"Academic search error."

def get_ai_recommendations(llm, recommender_prompt, profile, manual_list, count, language="English"):
    logger.info(f"开始生成 AI 推荐: 目标数量 {count}")
    print(f"\n[Agent 1] Generating recommendations...")  # 保持原有输出
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
        result = json.loads(match.group()) if match else []
        logger.info(f"AI 推荐完成: 生成 {len(result)} 所学校")
        return result
    except Exception as e:
        logger.error(f"AI 推荐失败: {e}")
        return []

def analyze_school(school_name, source_type, llm, analyzer_prompt, web_tool, sch_engine, 
                   interest, major, highest_school, current_degree, english_test, search_keywords,
                   target_countries=None, target_degree="PhD", major_en=None, keywords_en=None):
    # === 重试配置 ===
    MAX_RETRIES = 3  # 最多重试 3 次
    BASE_DELAY = 2   # 基础等待 2 秒
    logger.info(f"开始分析学校: {school_name}")
    msg = f"Scouting: {school_name}"
    print(msg)  # 保持原有输出
    try:
        # 适当调整学校名称，增加国家信息以提升搜索准确度
        refined_name = school_name
        if target_countries and len(target_countries) == 1 and "Global" not in target_countries:
            if target_countries[0] not in school_name:
                refined_name = f"{school_name} {target_countries[0]}"

        # 使用预翻译的结果，如果没有传入则回退到翻译
        search_major_en = major_en if major_en else ensure_english_term(llm, major)
        raw_keywords = search_keywords if search_keywords else interest
        search_keywords_en = keywords_en if keywords_en else ensure_english_term(llm, raw_keywords)
        
        # 中文意图检测
        has_chinese_intent = any(k in raw_keywords for k in ["中文", "华文", "Chinese", "Mandarin"])
        
        if has_chinese_intent:
            final_keywords = raw_keywords 
            logger.info(f"检测到中文/双语意图，保留原始关键词: {final_keywords}")
            print(f"[Search] 检测到中文/双语意图，保留原始关键词: {final_keywords}")  # 保持原有输出
        else:
            final_keywords = ensure_english_term(llm, raw_keywords)
        
        # 动态学位判断 (Master vs PhD)
        degree_term = target_degree if target_degree else "PhD"
        is_master = any(x in degree_term for x in ["Master", "MSc", "MA", "硕士"])

        if is_master:
            # 硕士模式：搜学费，不搜全奖
            search_degree_type = "Master"
            funding_query_part = "tuition fees curriculum admission requirements"
        else:
            # 博士模式：搜全奖 Stipend
            search_degree_type = "PhD"
            funding_query_part = "funding stipend tuition waiver assistantship handbook"

        # 语言搜索后缀 (既搜中文也搜英文官网)
        lang_suffix = ""
        if has_chinese_intent:
            lang_suffix = "AND (Chinese OR Mandarin OR bilingual)"

        user_test = "TOEFL IELTS"
        if english_test:
            if "Duolingo" in english_test or "DET" in english_test: user_test = "Duolingo minimum score"
            elif "IELTS" in english_test: user_test = "IELTS minimum score"
            elif "TOEFL" in english_test: user_test = "TOEFL minimum score"
        
        try:
            web_query = (
                f"{refined_name} {search_major_en} {search_degree_type} " 
                f"International Admission requirements{user_test} "
                f"funding package stipend assistantship "                 
                f"full tuition waiver health insurance benefits "         
                f"application deadline Fall "                             
                f"Student Handbook PDF "                                  
                f"{lang_suffix}" 
            )
        except Exception as e:
            logger.error(f"参数准备阶段失败 {school_name}: {e}")
            return None
        
        # === 2. 核心执行阶段 (带重试机制) ===
        # 只要 搜索、论文、LLM 任意一个环节报错，都会触发重试
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    print(f"    [Retry] {school_name} 第 {attempt+1} 次重试...")
                
                # --- A. 联网搜索 (修复版: 增加容错) ---
                try:
                    web_results = web_tool.invoke(web_query)
                    if isinstance(web_results, list) and len(web_results) > 0:
                        valid_results = [res for res in web_results if isinstance(res, dict)]
                        if valid_results:
                            web_context = "\n".join([f"Src: {res.get('url', 'N/A')}\nTxt: {res.get('content', '')}" for res in valid_results])
                        else:
                            web_context = "Search returned list but no valid dicts."
                    elif isinstance(web_results, str):
                        web_context = f"Search Engine Message: {web_results}"
                    else:
                        web_context = "No search results found."
                except Exception as e:
                    logger.warning(f"Web search parsing failed: {e}")
                    web_context = "Web search failed."
            
                # --- B. 学术搜索 ---
                # 注意：这一段必须在 try 内部，缩进要对齐
                academic_context = "Academic search skipped/failed."
                try:
                    academic_context = get_academic_papers(school_name, search_keywords_en, sch_engine, search_major_en)
                except Exception:
                    pass 

                # --- C. 准备 Prompt ---
                is_alumni = check_is_alumni(school_name, highest_school)
                is_alumni_str = "True" if is_alumni else "False"

                parser = JsonOutputParser(pydantic_object=SchoolReport)
                chain = analyzer_prompt | llm | parser
                
                # --- D. 调用 LLM ---
                result = chain.invoke({
                    "school_name": school_name, "interest": interest, 
                    "web_context": web_context, "academic_context": academic_context,
                    "highest_school": highest_school, "current_degree": current_degree, 
                    "english_test": english_test,
                    "is_alumni_str": is_alumni_str,
                    "format_instructions": parser.get_format_instructions()
                })
                
                # 成功！
                result['source'] = source_type
                if not result.get('source_url'): result['source_url'] = "N/A"
                logger.info(f"分析成功: {school_name} (匹配分: {result.get('research_fit_score', 'N/A')})")
                return result

            except Exception as e:
                # 这是对应 for 循环内部 try 的 except
                logger.warning(f"{school_name} 分析异常 (尝试 {attempt+1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BASE_DELAY * (2 ** attempt))
                else:
                    # === 3. 最终失败兜底 ===
                    print(f"    {school_name} Failed Completely: {e}")
                    return {
                        "school_name": school_name,
                        "source": source_type,
                        "research_fit_score": 0,
                        "language_req": "System Error (Analysis Failed)",
                        "funding_policy": "N/A",
                        "best_match_professor": "N/A",
                        "match_reason": "Analysis failed after retries due to network or API limits.",
                        "red_flags": f"System Error: {str(e)}",
                        "source_url": "N/A",
                        "application_deadline": "Unknown"
                    }
    except Exception as e:
        # 参数准备阶段的兜底
        logger.error(f"严重错误 {school_name}: {e}")
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
    # 自动打开浏览器
    try:
        abs_path = os.path.abspath("phd_report.html")
        webbrowser.open(f"file://{abs_path}")
    except Exception:
        pass
    return "phd_report.html"

if __name__ == "__main__":
    print("Please use 'streamlit run app.py'")