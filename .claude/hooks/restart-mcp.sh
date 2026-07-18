#!/bin/bash
# Kill orphaned MCP server processes from previous sessions
# so Claude Code spawns fresh connections on startup

pkill -f "tableau-mcp-server" 2>/dev/null
pkill -f "gmail-mcp" 2>/dev/null
pkill -f "google-calendar-mcp" 2>/dev/null
pkill -f "google-tasks-mcp" 2>/dev/null
pkill -f "google-analytics-mcp" 2>/dev/null
pkill -f "slack-mcp-server" 2>/dev/null
pkill -f "salesforce-mcp-server" 2>/dev/null
pkill -f "mcp-server-gdrive" 2>/dev/null
pkill -f "atlassian-mcp" 2>/dev/null
pkill -f "@anthropic-ai/playwright-mcp" 2>/dev/null
pkill -f "gemini-mcp-server" 2>/dev/null
pkill -f "@modelcontextprotocol/server-github" 2>/dev/null
pkill -f "@gpwork4u/google-sheets-mcp" 2>/dev/null
pkill -f "mcp-server-bigquery" 2>/dev/null
pkill -f "@a-bonus/google-docs-mcp" 2>/dev/null
pkill -f "@aiondadotcom/mcp-confluence-server" 2>/dev/null

# Small delay to let processes fully terminate
sleep 1
exit 0
