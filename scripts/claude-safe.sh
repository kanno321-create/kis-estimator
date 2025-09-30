#!/usr/bin/env bash
set -euo pipefail
echo "Starting Claude Code in SAFE auto-accept mode…"
claude --permission-mode auto-accept --allowedTools "Read" "Edit" "Bash(git *)"
