PhD-Scout: AI-Powered Research & Admission Agent

English | 中文说明

A "Human-in-the-Loop" AI Agent designed to automate the discovery of Ph.D. programs, verify admission requirements (DET/Funding), and quantify research fit.

<a name="english"></a>

English Description

The Backstory

I am currently applying for Computer Science Ph.D. programs in the US. The process involves analyzing hundreds of lab websites, which is repetitive and inefficient. I realized I was wasting hours on:

Checking Duolingo English Test (DET) acceptance (since I am on a tight schedule).

Digging for Full Funding guarantees.

Reading faculty profiles to find a true research match.

Generic rankings (US News) are useless for Ph.D. fit. I built this agent to automate the "scouting" phase, allowing me to focus on writing high-quality SOPs for the right schools.

Key Features

Hybrid Discovery: Combines your manual target list with AI-driven recommendations based on your specific profile (GPA, Papers, Interests).

Research Fit Scoring: Uses LLMs to semantically analyze faculty research interests and assigns a 0-100 Fit Score.

Hard Constraint Verification: Crawls admission pages to check for "Hard" requirements like DET acceptance and Funding policies.

The HTML Report: Generates a local interactive HTML report with color-coded scores and direct verification links.

Screenshot

![HTML Report Demo](assets/demo_report_english.png)

Tech Stack

Core: Python, LangChain

LLM: DeepSeek-V3 / OpenAI GPT-4o (Configurable)

Search: Tavily API (For real-time web crawling)

Visualization: Pandas, HTML/CSS generation

Quick Start

Clone the repo

git clone [https://github.com/yourusername/PhD-Scout.git](https://github.com/yourusername/PhD-Scout.git)
cd PhD-Scout



Install dependencies

pip install -r requirements.txt



Configure API Keys
Create a .env file in the root directory:

# LLM Configuration (DeepSeek Example)
LLM_API_KEY=sk-your-key
LLM_BASE_URL=[https://api.deepseek.com](https://api.deepseek.com)
LLM_MODEL_NAME=deepseek-chat

# Search Tool
TAVILY_API_KEY=tvly-your-key



Customize Your Profile
Edit config.yaml. This is the "brain" of the search. Input your GPA, research interests, and manual targets here.

Run the Agent

python main.py



The agent will generate an phd_report.html file and automatically open it in your browser.

The "Human-in-the-Loop" Philosophy

During development, I encountered an edge case with UTSA (University of Texas at San Antonio). My agent initially reported "No Duolingo Accepted" because the info was hidden inside a JavaScript dropdown menu that the crawler missed.

Lesson Learned: AI is a powerful filter, not a final decision-maker.

Design Choice: The tool provides a source_url for every claim.

Workflow: I use this tool to filter the top 10% of programs, but I manually verify the final shortlist before paying application fees.

<a name="chinese"></a>

中文说明 (Chinese)

为什么做这个工具？
我正在申请美国的计算机科学博士。整个过程要翻几百个实验室网站，特别重复又费时间。我发现，自己每天都在干这几件事：

查学校接不接受多邻国（Duolingo）——因为时间紧，不能考托福雅思；
找有没有全额奖学金（Full Funding）；
一个个看教授主页，找研究方向真正对得上的导师。
像 US News 这种排名，对博士申请基本没用。
所以我做了这个 AI 工具，自动完成前期“侦察”工作，让我能把精力放在写好真正值得投的 SOP 上。

主要功能
智能+手动结合推荐
你可以自己列目标学校，也能让 AI 根据你的 GPA、论文、兴趣，推荐可能适合你的“冷门宝藏”项目。
研究匹配打分（0–100 分）
用大模型分析教授的研究方向，算出你和他/她的匹配度，还会告诉你为什么匹配。
硬性条件自动查
自动爬官网，确认学校是否接受多邻国、是否保证全额资助等关键信息。
生成交互式 HTML 报告
运行完自动弹出一个网页报告：分数用颜色标出，每条结论都带官网链接，点一下就能核实。

用到的技术
核心：Python + LangChain
大模型：支持 DeepSeek-V3 或 GPT-4o（可配置）
网页搜索：Tavily API（实时抓取并整理网页内容）
报告生成：用 Pandas 处理数据，直接输出漂亮的 HTML 页面
快速开始
克隆项目

bash
12
git clone https://github.com/yourusername/PhD-Scout.gitcd PhD-Scout

安装依赖

bash
1
pip install -r requirements.txt

配置 API 密钥
在根目录新建一个 .env 文件，填入你的密钥：

env
1234567
# LLM 配置（以 DeepSeek 为例）LLM_API_KEY=sk-你的密钥LLM_BASE_URL=https://api.deepseek.comLLM_MODEL_NAME=deepseek-chat# 搜索工具TAVILY_API_KEY=tvly-你的密钥

填写你的背景信息
编辑 config.yaml 文件，填上你的 GPA、研究兴趣、想申的学校等。

运行

bash
1
python main.py

程序跑完后，会自动生成 phd_report.html 并在浏览器里打开。

截图

![HTML Report Demo](assets/demo_report_chinese.png)

“AI 辅助，人工确认”的设计原则
开发时我遇到一个例子：德州大学圣安东尼奥分校（UTSA）。
AI 一开始说“不接受多邻国”，因为官网信息藏在一个 JavaScript 下拉菜单里，爬虫没抓到。

这让我明白了一点：AI 只是帮你筛信息的工具，不能代替你做最终判断。

所以这个工具的设计原则是：

所有结论都附带原始链接（source_url），你可以一键点进去核实；
它帮你从几百个项目里快速找出最有可能的 10%，但最终是否申请，由你亲自确认。
适合像我一样时间紧、想高效申请 PhD 的人。
AI 负责干活，你负责决策。


Created by 

$$Sunny99$$

 - 2025 PhD Applicant