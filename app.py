# --- START OF FILE app.py ---

import streamlit as st
import pandas as pd
import os
import yaml
import concurrent.futures
from dotenv import load_dotenv

# 强制重新加载 main 模块（解决 Streamlit 缓存问题）
import importlib
import main
importlib.reload(main)

# 引入核心功能
from main import (
    init_services, 
    get_ai_recommendations, 
    analyze_school, 
    get_prompts, 
    generate_html_report, 
    deduplicate_school_list,
    ensure_english_term
)

# Page Config
st.set_page_config(
    page_title="PhD Scout Agent",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Environment Variables
load_dotenv()

# --- 1. UI Resources (Language Dictionary) ---
UI_TEXT = {
    "English": {
        # Sidebar
        "sidebar_title": "Settings",
        "provider_label": "LLM Provider",
        "provider_options": ["OpenAI", "DeepSeek", "Custom/Other"],
        "api_keys_header": "API Credentials",
        "openai_key_label": "API Key",
        "base_url_label": "Base URL",
        "model_name_label": "Model Name",
        "tavily_key_label": "Tavily Search API Key",
        "sch_key_label": "Semantic Scholar Key (Optional)",
        "load_config_button": "Load from config.yaml",
        "config_loaded_success": "Config loaded successfully!",
        "config_not_found_error": "config.yaml not found.",
        
        # Header
        "main_title": "PhD Scout Agent (Ultimate Edition)",
        "main_subtitle": "AI-driven assistant with Smart Strategy, Deduplication, and Waiver Detection.",
        
        # Profile Section
        "profile_header": "1. User Profile",
        "major_label": "Target Major / Discipline",
        "keywords_label": "Core Search Keywords",
        "keywords_help": "Crucial! E.g., 'Computer Vision' or 'Consumer Behavior'. AI uses this to find specific faculty.",
        "highest_school_label": "Highest Institution",
        "highest_school_help": "The university name is used to check for English waiver eligibility.",
        "current_degree_label": "Current Degree",
        "current_degree_help": "E.g., M.Sc. Data Science, B.S. Physics.",
        "gpa_label": "GPA",
        "paper_label": "Publications / Experience",
        "test_label": "English Test Score (Backup)",
        "interest_label": "Specific Research Interests",
        "degree_label": "Target Degree",
        "preferences_label": "Other Preferences",
        
        # Strategy Section
        "targets_header": "2. Targets & Strategy",
        "target_countries_label": "Target Countries",
        "manual_targets_label": "Manual Targets (One per line)",
        "rec_count_label": "AI Recommendation Count",
        "strategy_label": "Recommendation Strategy",
        "strategy_options": [
            "Balanced (Reputation & Fit)",
            "Top Tier (Ranking Focus)",
            "High Match (Research Focus)",
            "Safety (Funding Focus)"
        ],
        
        # Buttons & Status
        "start_button": "Start Agent Analysis",
        "error_missing_key": "Please provide both LLM API Key and Tavily API Key.",
        "status_running": "Agent is running...",
        "status_ai_recs": " AI Scouting: Generating school list (Strategy: {})...",
        "status_deduplicating": " Smart Deduplication: Merging AI & Manual lists...",
        "status_analyzing": " Deep Analysis: Scanning {} schools for '{}'...",
        "status_complete": " Analysis Complete!",
        
        # Results
        "results_header": "3. Analysis Report",
        "download_csv": "Download Data (CSV)",
        "download_html": "Download Report (HTML)",
        "no_results": "No results found. Please check your API keys or network.",
        "analyzed_item": "Scouted: {} (Fit Score: {})",
        "source_manual": "Manual",
        "source_ai": "AI Rec"
    },
    "Chinese": {
        # Sidebar
        "sidebar_title": "系统设置",
        "provider_label": "模型服务商 (LLM Provider)",
        "provider_options": ["OpenAI", "DeepSeek", "自定义/其他"],
        "api_keys_header": "API 凭证",
        "openai_key_label": "API Key (密钥)",
        "base_url_label": "Base URL (接口地址)",
        "model_name_label": "模型名称 (Model Name)",
        "tavily_key_label": "Tavily 搜索 API Key",
        "sch_key_label": "Semantic Scholar Key (选填)",
        "load_config_button": "从 config.yaml 加载配置",
        "config_loaded_success": "配置加载成功！",
        "config_not_found_error": "未找到 config.yaml 文件。",
        
        # Header
        "main_title": "PhD 留学申请助手 (终极版)",
        "main_subtitle": "AI 驱动的博士申请选校助手。集成智能去重、DeepSeek 支持与免语言判定。",
        
        # Profile Section
        "profile_header": "1. 个人背景 (User Profile)",
        "major_label": "申请专业/学科",
        "keywords_label": " 核心搜索词 (关键)",
        "keywords_help": "非常重要！例如：'Computer Vision' 或 'Consumer Behavior'。AI 将用此词搜索具体的实验室和导师。",
        "highest_school_label": "最高学历院校",
        "highest_school_help": "AI 将根据校名判断是否可以豁免语言成绩 (Waiver)。",
        "current_degree_label": "当前学位 / 所获学位",
        "current_degree_help": "例如：M.Sc. Data Science, B.S. Physics。",
        "gpa_label": "GPA",
        "paper_label": "科研经历/发表论文",
        "test_label": "英语成绩 (备用)",
        "interest_label": "具体研究方向",
        "degree_label": "申请学位",
        "preferences_label": "偏好设置 (地理位置等)",
        
        # Strategy Section
        "targets_header": "2. 目标与策略",
        "target_countries_label": "目标国家/地区",
        "manual_targets_label": "手动指定学校 (每行一个)",
        "rec_count_label": "AI 补充推荐数量",
        "strategy_label": "AI 选校策略",
        "strategy_options": [
            "均衡策略 (平衡综排与匹配度)",
            "冲刺名校 (关注 Top Tier)",
            "高匹配/潜力股 (忽视综排，只看方向)",
            "保底/稳妥 (关注录取率与资金)"
        ],
        
        # Buttons & Status
        "start_button": " 开始智能分析",
        "error_missing_key": "错误：请提供 LLM API Key 和 Tavily API Key。",
        "status_running": "正在启动 Agent...",
        "status_ai_recs": " AI 侦察中: 正在生成推荐列表 (策略: {})...",
        "status_deduplicating": " 智能去重: 正在合并手动与 AI 推荐列表...",
        "status_analyzing": " 深度分析: 正在扫描 {} 所学校 (方向: {})...",
        "status_complete": " 分析完成！",
        
        # Results
        "results_header": "3. 分析报告",
        "download_csv": "下载数据 (CSV)",
        "download_html": "下载完整报告 (HTML)",
        "no_results": "未找到结果，请检查 API Key 或网络连接。",
        "analyzed_item": "已分析: {} (匹配分: {})",
        "source_manual": "手动目标",
        "source_ai": "AI 推荐"
    }
}

# --- 2. Strategy Internal Mapping ---
STRATEGY_MAPPING = {
    0: "Balanced",
    1: "Top Tier (冲刺名校)",
    2: "High Match / Hidden Gems (高匹配/潜力股)",
    3: "Safety / Safe Bets (保底/稳妥)"
}

def load_config():
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None

# --- Sidebar: Configuration ---
# ⚠️ Key Fixed: 语言选择
language = st.sidebar.selectbox("Language / 语言", ["English", "Chinese"], index=1, key="app_language")

if "last_lang" not in st.session_state:
    st.session_state["last_lang"] = language

if st.session_state["last_lang"] != language:
    st.session_state["last_lang"] = language
    st.rerun() # 强制立刻刷新页面

text = UI_TEXT[language]

st.sidebar.title(text["sidebar_title"])

# Provider Selection
st.sidebar.subheader(text["api_keys_header"])
# ⚠️ Key Fixed: 服务商选择
provider_idx = st.sidebar.selectbox(
    text["provider_label"], 
    range(len(text["provider_options"])), 
    format_func=lambda x: text["provider_options"][x],
    index=1,
    key="llm_provider" 
)
selected_provider_logic = ["OpenAI", "DeepSeek", "Custom"][provider_idx]

# Auto-fill Logic
default_base_url = "https://api.openai.com/v1"
default_model = "gpt-4o-mini"
if selected_provider_logic == "DeepSeek":
    default_base_url = "https://api.deepseek.com"
    default_model = "deepseek-chat"
elif selected_provider_logic == "Custom":
    default_base_url = ""
    default_model = ""

# ⚠️ Keys Fixed for Inputs
api_key = st.sidebar.text_input(text["openai_key_label"], value="", type="password", key="input_api_key")
base_url = st.sidebar.text_input(text["base_url_label"], value=default_base_url, key="input_base_url")
model_name = st.sidebar.text_input(text["model_name_label"], value=default_model, key="input_model_name")

st.sidebar.markdown("---")
tavily_api_key = st.sidebar.text_input(text["tavily_key_label"], value="", type="password", key="input_tavily_key")
sch_api_key = st.sidebar.text_input(text["sch_key_label"], value="", type="password", key="input_sch_key")

if st.sidebar.button(text["load_config_button"], key="btn_load_config"):
    new_config = load_config() # 加载新配置
    if new_config:
        # 1. 更新主 config 状态
        st.session_state['config'] = new_config
        
        # 2. 【关键修复】强制更新所有控件绑定的 Session State Key
        # 如果不加这一步，界面上的输入框不会变
        
        # Profile 部分
        p = new_config.get('profile', {})
        st.session_state['input_major'] = p.get('major', '')
        st.session_state['input_keywords'] = p.get('search_keywords', '')
        st.session_state['input_highest_school'] = p.get('highest_school', '')
        st.session_state['input_current_degree'] = p.get('current_degree', '')
        st.session_state['input_gpa'] = str(p.get('gpa', '')) # 确保转为字符串
        st.session_state['input_paper'] = p.get('paper', '')
        st.session_state['input_english_test'] = p.get('english_test', '')
        st.session_state['input_interest'] = p.get('research_interest', '')
        st.session_state['input_target_degree'] = p.get('target_degree', 'Ph.D.')
        st.session_state['input_preferences'] = p.get('preferences', '')
        
        # Targets 部分
        # 注意：Multiselect 需要 List，Text Area 需要 String
        st.session_state['input_countries'] = new_config.get('target_countries', ["United States"])
        
        manual_list = new_config.get('manual_targets', [])
        if isinstance(manual_list, list):
            st.session_state['input_manual_targets'] = "\n".join(manual_list)
        else:
            st.session_state['input_manual_targets'] = str(manual_list)
            
        # Settings 部分
        s = new_config.get('settings', {})
        st.session_state['input_rec_count'] = int(s.get('recommendation_count', 3))

        st.sidebar.success(text["config_loaded_success"])
        st.rerun() # 强制刷新页面，让输入框读取 Session State 的新值
    else:
        st.sidebar.error(text["config_not_found_error"])

# --- Main Area ---
st.title(text["main_title"])
st.markdown(text["main_subtitle"])

# Initialize Session State
if 'config' not in st.session_state:
    st.session_state['config'] = {
        'profile': {
            'major': 'Computer Science', 
            'search_keywords': '', 
            'highest_school': '', 'current_degree': '',
            'gpa': '', 'paper': '', 'english_test': '', 
            'research_interest': '', 'target_degree': 'Ph.D.', 'preferences': ''
        },
        'target_countries': ['United States'],
        'manual_targets': [],
        'settings': {'recommendation_count': 3}
    }

config = st.session_state['config']

# --- Section 1: User Profile ---
# 注意：即使 Label 根据 text[] 变化，key 始终保持不变，这样内容就不会丢失。
with st.expander(text["profile_header"], expanded=True):
    col_major1, col_major2 = st.columns(2)
    with col_major1:
        major = st.text_input(text["major_label"], 
            value=config['profile'].get('major', 'Computer Science'),
            key="input_major")
    with col_major2:
        search_keywords = st.text_input(text["keywords_label"], 
            value=config['profile'].get('search_keywords', ''),
            help=text["keywords_help"],
            key="input_keywords")

    col_edu1, col_edu2 = st.columns(2)
    with col_edu1:
        highest_school = st.text_input(text["highest_school_label"], 
            value=config['profile'].get('highest_school', ''), 
            help=text["highest_school_help"],
            key="input_highest_school")
    with col_edu2:
        current_degree = st.text_input(text["current_degree_label"], 
            value=config['profile'].get('current_degree', ''),
            help=text["current_degree_help"],
            key="input_current_degree")
            
    col1, col2 = st.columns(2)
    with col1:
        gpa = st.text_input(text["gpa_label"], 
            value=config['profile'].get('gpa', ''), 
            key="input_gpa")
        paper = st.text_area(text["paper_label"], 
            value=config['profile'].get('paper', ''), 
            key="input_paper")
        english_test = st.text_input(text["test_label"], 
            value=config['profile'].get('english_test', ''), 
            key="input_english_test")
    with col2:
        research_interest = st.text_area(text["interest_label"], 
            value=config['profile'].get('research_interest', ''), 
            key="input_interest")
        target_degree = st.text_input(text["degree_label"], 
            value=config['profile'].get('target_degree', 'Ph.D.'), 
            key="input_target_degree")
        preferences = st.text_area(text["preferences_label"], 
            value=config['profile'].get('preferences', ''), 
            key="input_preferences")

# --- Section 2: Targets & Strategy ---
with st.expander(text["targets_header"], expanded=True):
    default_countries = config.get('target_countries', ["United States"])
    available_countries = ["United States", "United Kingdom", "Canada", "Singapore", "Hong Kong", "Switzerland", "Germany", "Australia", "Japan"]
    for c in default_countries:
        if c not in available_countries: available_countries.append(c)
        
    target_countries = st.multiselect(
        text["target_countries_label"], 
        available_countries,
        default=default_countries,
        key="input_countries"
    )
    
    manual_targets_str = st.text_area(text["manual_targets_label"], 
        value="\n".join(config.get('manual_targets', [])), 
        key="input_manual_targets")
    
    col_strat1, col_strat2 = st.columns(2)
    with col_strat1:
        rec_count = st.number_input(text["rec_count_label"], 
            min_value=0, max_value=20, 
            value=config['settings'].get('recommendation_count', 3),
            key="input_rec_count")
    with col_strat2:
        strategy_idx = st.selectbox(
            text["strategy_label"], 
            range(len(text["strategy_options"])),
            format_func=lambda x: text["strategy_options"][x],
            index=2,
            key="input_strategy" 
        )
        actual_rec_strategy = STRATEGY_MAPPING[strategy_idx]

# --- Action Section ---
if st.button(text["start_button"], type="primary", use_container_width=True, key="btn_start"):
    if not api_key or not tavily_api_key:
        st.error(text["error_missing_key"])
    else:
        # Prepare Data
        current_profile = {
            'major': major,
            'search_keywords': search_keywords,
            'highest_school': highest_school,
            'current_degree': current_degree,
            'gpa': gpa, 'paper': paper, 'english_test': english_test,
            'research_interest': research_interest, 'target_degree': target_degree,
            'preferences': preferences
        }
        manual_targets = [s.strip() for s in manual_targets_str.split('\n') if s.strip()]
        
        try:
            if tavily_api_key: os.environ["TAVILY_API_KEY"] = tavily_api_key

            llm, web_tool, sch_engine = init_services(
                api_key=api_key, 
                base_url=base_url, 
                model_name=model_name,
                sch_api_key=sch_api_key
            )
            
            recommender_prompt, analyzer_prompt = get_prompts(language, major, target_countries, actual_rec_strategy)
            
            status_container = st.status(text["status_running"], expanded=True)
            
            # 1. AI Recommendations
            countries_str = ", ".join(target_countries)
            status_container.write(text["status_ai_recs"].format(text["strategy_options"][strategy_idx], countries_str))
            
            raw_school_list = [{"name": s, "source": text["source_manual"]} for s in manual_targets]
            
            if rec_count > 0:
                ai_schools = get_ai_recommendations(llm, recommender_prompt, current_profile, manual_targets, rec_count, language)
                for s in ai_schools:
                    raw_school_list.append({"name": s, "source": text["source_ai"]})
            
            # 2. Smart Deduplication
            status_container.write(text["status_deduplicating"])
            final_list = deduplicate_school_list(llm, raw_school_list)
            
            # 3. 补足逻辑：如果去重后 AI 推荐数量不足，再补推荐
            target_total = len(manual_targets) + rec_count
            current_count = len(final_list)
            if current_count < target_total and rec_count > 0:
                shortfall = target_total - current_count
                # 收集已有学校名，避免重复推荐
                existing_names = [item['name'] for item in final_list]
                
                extra_schools = get_ai_recommendations(
                    llm, recommender_prompt, current_profile, 
                    existing_names,  # 把已有的都传进去避免重复
                    shortfall, 
                    language
                )
                # 自动保安逻辑
                # 定义一个简单的清洗函数，把 "SUSS (Singapore)" 和 "SUSS" 视为同一个
                def quick_clean(n):
                    return str(n).lower().replace(" ", "").replace("university", "").replace("of", "").replace("the", "")

                # 建立现有学校的“指纹库”
                existing_fingerprints = set(quick_clean(item['name']) for item in final_list)

                for s in extra_schools:
                    # 只有当新学校的指纹 不在 指纹库里时，才添加
                    if quick_clean(s) not in existing_fingerprints:
                        final_list.append({"name": s, "source": text["source_ai"]})
                        # 同时更新指纹库，防止 extra_schools 内部自己重复
                        existing_fingerprints.add(quick_clean(s))
                    else:
                        print(f"[System] 自动拦截了重复推荐: {s}")
                
                # 再次去重（以防万一）
                final_list = deduplicate_school_list(llm, final_list)
            
            # 4. Pre-translate (避免在循环中重复调用 LLM)
            major_en = ensure_english_term(llm, major)
            keywords_en = ensure_english_term(llm, search_keywords)
            
            # 4. Parallel Analysis
            status_container.write(text["status_analyzing"].format(len(final_list), major))
            results = []
            progress_bar = status_container.progress(0)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_school = {
                    executor.submit(
                        analyze_school, 
                        item['name'], 
                        item['source'], 
                        llm, 
                        analyzer_prompt, 
                        web_tool, 
                        sch_engine, 
                        research_interest,
                        major, 
                        highest_school,
                        current_degree,
                        english_test,
                        search_keywords,
                        target_countries=target_countries,
                        target_degree=target_degree,
                        major_en=major_en,
                        keywords_en=keywords_en
                    ): item for item in final_list
                }
                
                completed_count = 0
                for future in concurrent.futures.as_completed(future_to_school):
                    data = future.result()
                    if data:
                        results.append(data)
                        status_container.write(text["analyzed_item"].format(data['school_name'], data['research_fit_score']))
                    
                    completed_count += 1
                    progress_bar.progress(completed_count / len(final_list))
            
            status_container.update(label=text["status_complete"], state="complete", expanded=False)
            
            if results:
                df = pd.DataFrame(results).sort_values(by=['research_fit_score'], ascending=False)
                
                st.subheader(text["results_header"])
                st.dataframe(df)
                
                report_file = generate_html_report(df, language=language)
                
                col_down1, col_down2 = st.columns(2)
                with col_down1:
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(text["download_csv"], csv, "phd_strategy_report.csv", "text/csv")
                
                with col_down2:
                    with open(report_file, "rb") as f:
                        st.download_button(text["download_html"], f, "phd_report.html", "text/html")
                
            else:
                st.warning(text["no_results"])
                
        except Exception as e:
            st.error(f"Error: {e}")