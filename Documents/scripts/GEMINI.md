# GEMINI.md

This file contains the foundational mandates and project-specific instructions for Gemini CLI. These instructions take absolute precedence over general workflows and tool defaults.

## 🚀 Project Overview
This project consists of various Python-based tools and Streamlit applications for AI-powered assistance, market intelligence reporting, and integration with several MCP (Model Context Protocol) services.

## 🏗️ Architectural Principles
- **Streamlit-based UIs:** Applications like `chat_app.py` and `cowork.py` use Streamlit for the user interface.
- **Context Injection:** `cowork.py` utilizes a sidebar `project_context` for system prompt injection at request time.
- **Streaming Responses:** Preferred interaction model for chat applications is streaming via `client.messages.stream()`.

## 💻 Coding Standards
- **Language/Framework:** Python 3.9.6, Streamlit 1.50.0, Anthropic SDK.
- **Environment Variables:** `ANTHROPIC_API_KEY` is required for all scripts.
- **Dependencies:** Managed via `pip3 install -r ~/Documents/scripts/cowork/requirements.txt`.

## 🧪 Testing Requirements
- **Manual Verification:** Use `python3 ~/Documents/scripts/test_prompt.py` to test prompts by filling in `project_context` and `user_request`.

## 🛠️ Tool Preferences
- **Python Version:** Python 3.9.6
- **MCP Services:** The following services are configured and should be utilized via their respective MCP servers:
    - **Tableau:** Cars Commerce Tableau (us-west-2b, site: cars)
    - **Gmail:** jcrawley@cars.com (OAuth refresh token at `~/.claude/tokens/gmail_jcrawley.json`)
    - **Google Calendar/Drive:** OAuth via `~/gcp-oauth.keys.json`
    - **Google Tasks:** Refresh token in `~/.claude/settings.json`
    - **Google Analytics:** ADC at `~/.claude/ga_tokens/gafield_adc.json` and `gafield1_adc.json`
    - **Atlassian:** Jira + Confluence (carscommerce.atlassian.net)
    - **Salesforce:** SF CLI at `~/.npm-global/bin/sf`
    - **Slack:** Cars Commerce workspace (xoxb + xoxp tokens)
    - **Playwright:** Browser automation

## 🔄 Workflow Specifics
- **Streamlit Apps:** Run from their respective directories using `streamlit run <path_to_script>`.
- **Market Reports:** Generated via `python3 ~/Documents/scripts/generate_market_report.py` and output to `~/Documents/Reports/HamptonRoads/`.
- **Credential Management:** Gmail access tokens expire every hour; the refresh token in `gmail_jcrawley.json` is permanent.
