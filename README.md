PhD-Scout: AI-Powered Research & Admission Agent

[🇺🇸 English](README.md) | [🇨🇳 中文说明](README.zh-CN.md)

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

git clone [https://github.com/sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection.git](https://github.com/sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection.git)
cd PhD-Scout-AI-Agent-for-PhD-Program-Selection




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

Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&type=Date)](https://star-history.com/#sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&Date)

Created by Sunny99

 - 2025 PhD Applicant