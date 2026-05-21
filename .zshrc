# Anthropic API key — used by cowork.py only
# dealer_health.py now uses `claude -p` (login auth); Claude Code CLI also uses login
# To store: security add-generic-password -s 'anthropic-api-key' -a "$USER" -w 'YOUR_KEY'
export ANTHROPIC_API_KEY="$(security find-generic-password -s 'anthropic-api-key' -w 2>/dev/null)"

# Tableau PAT — used by biz_scan.py, investigation_dashboard.py, investigation_triggers.py
# To rotate: security delete-generic-password -a jcrawley -s tableau-pat
#            security add-generic-password -a jcrawley -s tableau-pat -w 'NEW_SECRET'
export TABLEAU_PAT_SECRET="$(security find-generic-password -a jcrawley -s 'tableau-pat' -w 2>/dev/null)"
export TABLEAU_PAT_NAME="Claude"

# PATH
export PATH=~/.npm-global/bin:$PATH
export PATH="$HOME/.claude/bin:$PATH"
export PATH="$HOME/.fzf/bin:$PATH"

# Environment
. "$HOME/.local/bin/env"

# History
HISTSIZE=50000
SAVEHIST=50000
HISTFILE=~/.zsh_history
setopt SHARE_HISTORY
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_SPACE
setopt EXTENDED_HISTORY

# Navigation
setopt AUTO_CD
setopt AUTO_PUSHD

# Completion
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select

# Key bindings — history search by prefix
bindkey '^[[A' history-search-backward
bindkey '^[[B' history-search-forward

# --- Aliases ---
alias scripts='cd ~/Documents/scripts'
alias reports='cd ~/Documents/Reports'
alias tab='cd ~/Documents/Tableau'
alias chat='python3 -m streamlit run ~/Documents/scripts/chat_app.py'
alias cowork='python3 -m streamlit run ~/Documents/scripts/cowork/cowork.py'
alias dh='python3 -m streamlit run ~/Documents/scripts/dealer_health.py'
alias gs='git status'
alias gl='git log --oneline -20'
alias copy='pbcopy'
alias paste='pbpaste'
alias showfiles='defaults write com.apple.finder AppleShowAllFiles YES; killall Finder'
alias hidefiles='defaults write com.apple.finder AppleShowAllFiles NO; killall Finder'

# Better defaults (only if tools are installed)
command -v bat &>/dev/null && alias cat='bat --paging=never'
command -v eza &>/dev/null && alias ls='eza --icons' && alias ll='eza -la --icons --git'

# --- Tool Integrations ---
command -v starship &>/dev/null && eval "$(starship init zsh)"
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh
