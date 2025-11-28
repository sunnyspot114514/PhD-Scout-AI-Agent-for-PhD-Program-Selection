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

Human-in-the-Loop Philosophy

While testing the agent, I ran into an interesting case with UTSA (University of Texas at San Antonio).
The tool originally said “Duolingo not accepted,” but the requirement was actually hidden inside a JavaScript dropdown, so the crawler didn’t catch it.

This showed me something important:

AI can narrow options fast, but it shouldn’t make the final call.

So I designed the tool with this workflow in mind:

Every result includes a source_url so you can quickly double-check it.

Use the agent to filter down to the top 10–15% of programs.

Do a manual verification before applying or paying any fees.

Simple rule: let AI speed up the search, but keep a human in the final loop.

Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&type=Date)](https://star-history.com/#sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&Date)

Created by Sunny99

 - 2025 PhD Applicant
