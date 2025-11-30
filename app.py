import streamlit as st
import pandas as pd
import os
import yaml
import concurrent.futures
from dotenv import load_dotenv
from main import init_services, get_ai_recommendations, analyze_school, get_prompts, generate_html_report

# Page Config (No Emojis)
st.set_page_config(
    page_title="PhD Scout Agent",
    layout="wide"
)

# Load Environment Variables (only for internal use if needed, not for UI defaults)
load_dotenv()

# --- Language Constants ---
UI_TEXT = {
    "English": {
        "sidebar_title": "Settings",
        "api_keys_header": "API Keys",
        "openai_key_label": "OpenAI API Key",
        "base_url_label": "Base URL (Optional)",
        "model_name_label": "Model Name",
        "tavily_key_label": "Tavily API Key",
        "sch_key_label": "Semantic Scholar Key (Optional)",
        "load_config_button": "Load from config.yaml",
        "config_loaded_success": "Config loaded successfully!",
        "config_not_found_error": "config.yaml not found.",
        "main_title": "PhD Scout Agent",
        "main_subtitle": "AI-driven assistant for finding your perfect Ph.D. program match.",
        "profile_header": "User Profile",
        "gpa_label": "GPA",
        "paper_label": "Publications",
        "test_label": "English Test",
        "interest_label": "Research Interest",
        "degree_label": "Target Degree",
        "preferences_label": "Preferences",
        "targets_header": "Target Schools",
        "manual_targets_label": "Manual Targets (One per line)",
        "rec_count_label": "AI Recommendation Count",
        "start_button": "Start Analysis",
        "error_missing_key": "Please provide both OpenAI API Key and Tavily API Key.",
        "status_running": "Running Analysis...",
        "status_ai_recs": "Generating AI Recommendations...",
        "status_analyzing": "Analyzing {} schools...",
        "status_complete": "Analysis Complete!",
        "results_header": "Analysis Results",
        "download_csv": "Download CSV",
        "download_html": "Download HTML Report",
        "no_results": "No results found.",
        "rec_item": "Recommended: {}",
        "analyzed_item": "{} (Score: {})"
    },
    "Chinese": {
        "sidebar_title": "设置",
        "api_keys_header": "API 密钥",
        "openai_key_label": "OpenAI API Key",
        "base_url_label": "Base URL (选填)",
        "model_name_label": "模型名称",
        "tavily_key_label": "Tavily API Key",
        "sch_key_label": "Semantic Scholar Key (选填)",
        "load_config_button": "从 config.yaml 加载",
        "config_loaded_success": "配置加载成功！",
        "config_not_found_error": "未找到 config.yaml 文件。",
        "main_title": "PhD 留学申请助手",
        "main_subtitle": "AI 驱动的博士申请选校助手，助你找到最匹配的项目。",
        "profile_header": "个人背景",
        "gpa_label": "GPA",
        "paper_label": "发表论文",
        "test_label": "英语成绩",
        "interest_label": "研究方向",
        "degree_label": "申请学位",
        "preferences_label": "偏好设置",
        "targets_header": "目标院校",
        "manual_targets_label": "手动目标 (每行一个)",
        "rec_count_label": "AI 推荐数量",
        "start_button": "开始分析",
        "error_missing_key": "请提供 OpenAI API Key 和 Tavily API Key。",
        "status_running": "正在运行分析...",
        "status_ai_recs": "正在生成 AI 推荐...",
        "status_analyzing": "正在分析 {} 所学校...",
        "status_complete": "分析完成！",
        "results_header": "分析结果",
        "download_csv": "下载 CSV",
        "download_html": "下载 HTML 报告",
        "no_results": "未找到结果。",
        "rec_item": "推荐: {}",
        "analyzed_item": "{} (得分: {})"
    }
}

def load_config():
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None

# --- Sidebar: Configuration ---
# Language Selection first
language = st.sidebar.selectbox("Language / 语言", ["English", "Chinese"], index=1)
text = UI_TEXT[language]

st.sidebar.title(text["sidebar_title"])

# API Keys
st.sidebar.subheader(text["api_keys_header"])
# Default values are empty strings as requested
api_key = st.sidebar.text_input(text["openai_key_label"], value="", type="password")
base_url = st.sidebar.text_input(text["base_url_label"], value="https://api.openai.com/v1")
model_name = st.sidebar.text_input(text["model_name_label"], value="gpt-4o-mini")
tavily_api_key = st.sidebar.text_input(text["tavily_key_label"], value="", type="password")
sch_api_key = st.sidebar.text_input(text["sch_key_label"], value="", type="password")

# Load Config Button
if st.sidebar.button(text["load_config_button"]):
    config = load_config()
    if config:
        st.session_state['config'] = config
        st.sidebar.success(text["config_loaded_success"])
    else:
        st.sidebar.error(text["config_not_found_error"])

# --- Main Area ---
st.title(text["main_title"])
st.markdown(text["main_subtitle"])

# Initialize Session State for Config
if 'config' not in st.session_state:
    st.session_state['config'] = {
        'profile': {
            'gpa': '', 'paper': '', 'english_test': '', 'research_interest': '', 'target_degree': 'Ph.D. in CS', 'preferences': ''
        },
        'manual_targets': [],
        'settings': {'recommendation_count': 3}
    }

config = st.session_state['config']

# User Profile Form
with st.expander(text["profile_header"], expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        gpa = st.text_input(text["gpa_label"], value=config['profile'].get('gpa', ''))
        paper = st.text_area(text["paper_label"], value=config['profile'].get('paper', ''))
        english_test = st.text_input(text["test_label"], value=config['profile'].get('english_test', ''))
    with col2:
        research_interest = st.text_area(text["interest_label"], value=config['profile'].get('research_interest', ''))
        target_degree = st.text_input(text["degree_label"], value=config['profile'].get('target_degree', 'Ph.D. in CS'))
        preferences = st.text_area(text["preferences_label"], value=config['profile'].get('preferences', ''))

# Target Schools
with st.expander(text["targets_header"], expanded=True):
    manual_targets_str = st.text_area(text["manual_targets_label"], value="\n".join(config.get('manual_targets', [])))
    rec_count = st.number_input(text["rec_count_label"], min_value=0, max_value=10, value=config['settings'].get('recommendation_count', 3))

# Action Button
if st.button(text["start_button"], type="primary"):
    if not api_key:
        st.error(text["error_missing_key"])
    else:
        # Update Config Object
        current_profile = {
            'gpa': gpa, 'paper': paper, 'english_test': english_test,
            'research_interest': research_interest, 'target_degree': target_degree,
            'preferences': preferences
        }
        manual_targets = [s.strip() for s in manual_targets_str.split('\n') if s.strip()]
        
        # Initialize Agent
        try:
            # Set Tavily API Key in env if provided
            if tavily_api_key:
                os.environ["TAVILY_API_KEY"] = tavily_api_key

            # Initialize services
            llm, web_tool, sch_engine = init_services(
                api_key=api_key, 
                base_url=base_url, 
                model_name=model_name,
                sch_api_key=sch_api_key
            )
            # Get prompts
            recommender_prompt, analyzer_prompt = get_prompts(language)
            
            status_container = st.status(text["status_running"], expanded=True)
            
            # 1. AI Recommendations
            status_container.write(text["status_ai_recs"])
            src_manual = "手动目标" if language == "Chinese" else "Manual Target"
            src_ai = "AI 推荐" if language == "Chinese" else "AI Recommendation"
            
            final_list = [{"name": s, "source": src_manual} for s in manual_targets]
            
            if rec_count > 0:
                ai_schools = get_ai_recommendations(llm, recommender_prompt, current_profile, manual_targets, rec_count, language)
                for s in ai_schools:
                    final_list.append({"name": s, "source": src_ai})
                    status_container.write(text["rec_item"].format(s))
            
            # 2. Analysis
            status_container.write(text["status_analyzing"].format(len(final_list)))
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
                        research_interest
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
                
                # Generate HTML Report
                report_file = generate_html_report(df, language=language)
                
                # Download Buttons
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(text["download_csv"], csv, "phd_strategy_report.csv", "text/csv")
                
                with open(report_file, "rb") as f:
                    st.download_button(text["download_html"], f, "phd_report.html", "text/html")
                
            else:
                st.warning(text["no_results"])
                
        except Exception as e:
            st.error(f"Error: {e}")
