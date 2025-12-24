# PhD-Scout: AI-Powered Research & Admission Agent

[![Open in Spaces](https://huggingface.co/datasets/huggingface/badges/raw/main/open-in-hf-spaces-sm-dark.svg)](https://huggingface.co/spaces/sunny114514/PhD-Scout)

[🇺🇸 English](README.md) | [🇨🇳 中文说明](README.zh-CN.md)

PhD-Scout is an AI-driven assistant designed to streamline the early-stage search and evaluation of Ph.D. programs.
It focuses on three essential tasks that typically require extensive manual effort:

**Identifying programs that align with a specific research background**

**Verifying admission requirements such as Duolingo English Test (DET) acceptance**

**Confirming funding policies and other hard constraints**

This tool was originally developed to support my own Ph.D. application process in Computer Science. It is now released as an open-source project to assist others who face similar challenges.

## Background and Motivation

During the graduate school search process, applicants frequently spend significant time navigating:

**Faculty profiles scattered across departmental websites**

**Inconsistent or hard-to-locate information about required English tests**

**Funding guarantees that vary by department and institution**

**The lack of reliable indicators for research compatibility**

**The inefficiency of manually comparing dozens or hundreds of programs**

**Traditional rankings (such as US News) provide little insight into actual research fit.**

PhD-Scout aims to address this gap by automating the initial scouting stage, allowing applicants to focus on evaluating a refined, high-quality shortlist and preparing targeted statements of purpose.

## Live Demo

Experience the full functionality directly on Hugging Face Spaces without any installation:

 **[Click here to try PhD Scout online](https://huggingface.co/spaces/sunny114514/PhD-Scout)**


# Key Features

## 1. Hybrid Program Discovery

Combines manually specified target programs with AI-generated recommendations based on user background (GPA, publications, research keywords).

## 2. Research Fit Analysis

*   **Dual-Source Verification**: Combines Google Search (Tavily) for admission info with **Semantic Scholar API** for academic depth.
*   **Fit Scoring**: Uses LLM to analyze faculty papers against your keywords, generating a "Research Fit Score" (0–100) and identifying specific professors.
*   **Alumni Bonus**: Automatically detects and boosts scores if the target school has alumni connections (configurable).

## 3. Verification of Hard Constraints

Automatically checks program webpages for critical admission requirements, including:

Duolingo English Test (DET) acceptance

Funding policies

GPA and prerequisite expectations

Each claim includes a source URL for manual verification.

## 4. Interactive Web Interface (Streamlit)

Provides a user-friendly interface for configuring inputs, running analyses, and exporting results.

## 5. Configurable Architecture

Supports both CLI and GUI modes.
Allows customization of:

LLM providers (OpenAI, DeepSeek, etc.)

Search tools (Tavily API)

Program lists and user profiles

Output formats

Technology Stack

Core: Python

Framework: LangChain

LLM Providers: OpenAI GPT-4o, DeepSeek V3 (configurable)

Search Engine: Tavily API

GUI: Streamlit

## Interface Preview

PhD-Scout provides a user-friendly Streamlit dashboard, allowing you to easily configure your profile, strategy, and API keys without touching the code.

![screenshot](./assets/demo_GUI_english.png)
*(The Configuration Dashboard)*

# Quick Start

## 1. Clone the Repository

```bash
git clone https://github.com/sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection.git
cd PhD-Scout-AI-Agent-for-PhD-Program-Selection 
```

## 2. Install Dependencies

```bash
pip install -r requirements.txt
```

## 3. Configure API Keys

First, obtain your API keys from the following providers:

* **DeepSeek API** :  
    https://platform.deepseek.com/api_keys
* **Tavily Web Search API** (For real-time school requirements):  
    https://app.tavily.com/

Then, create a `.env` file in the project root:

# LLM Configuration
 
```bash
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-chat
 ```

# Search Tool

```bash
TAVILY_API_KEY=your-tavily-key
```

## 4. Run the Agent

Option A: Command Line (CLI)

Edit the config.yaml file

Execute:

```python
python main.py
```

Option B: Web Interface (GUI)

```python
streamlit run app.py
```

The application will open at:

http://localhost:8501

# Report Example

![screenshot](./assets/demo_report_english.png)

# Human-in-the-Loop Design

During testing, an issue occurred with UTSA (University of Texas at San Antonio).
The agent reported that DET was not accepted. However, the official information was located inside a JavaScript-rendered dropdown menu that the crawler could not access.

This revealed an important principle:

AI tools can filter and accelerate research, but manual verification remains necessary for critical decisions.

For this reason, every automated claim generated by PhD-Scout includes a source URL.
Users are encouraged to review final results before submitting applications or paying fees.

# Roadmap

- [ ] Parallel processing optimization (Current: ThreadPool)

- [x] Bilingual reporting (English/Chinese) - *Implemented*

- [x] Streamlit graphical interface - *Implemented*

- [x] Semantic Scholar integration - *Implemented*

- [ ] Automatic email draft generator for contacting potential advisors

# License

This project is released under the MIT License.
See the LICENSE file for details.


# Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&type=Date)](https://star-history.com/#sunnyspot114514/PhD-Scout-AI-Agent-for-PhD-Program-Selection&Date)

# Author

Created and maintained by Chen Xiwei, 2025 Ph.D. applicant.
