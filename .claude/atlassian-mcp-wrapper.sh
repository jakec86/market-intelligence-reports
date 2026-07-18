#!/bin/bash
# Wrapper for atlassian-mcp with env vars; token pulled from Keychain at launch
ATLASSIAN_API_TOKEN="$(security find-generic-password -a jcrawley -s atlassian-api-token -w)"
export CONFLUENCE_URL='https://carscommerce.atlassian.net/wiki'
export CONFLUENCE_USERNAME='jcrawley@cars.com'
export CONFLUENCE_API_TOKEN="$ATLASSIAN_API_TOKEN"
export JIRA_URL='https://carscommerce.atlassian.net'
export JIRA_BASE_URL='https://carscommerce.atlassian.net'
export JIRA_SITE='carscommerce.atlassian.net'
export JIRA_EMAIL='jcrawley@cars.com'
export JIRA_USERNAME='jcrawley@cars.com'
export JIRA_API_TOKEN="$ATLASSIAN_API_TOKEN"
exec /Users/jcrawley/.npm-global/bin/atlassian-mcp "$@"
