# Claude Code Dev Container (Windows VS Code friendly)
FROM node:20-bullseye

# Basic tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl ca-certificates python3 python3-pip bash sudo jq \
 && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm i -g @anthropic-ai/claude-code

WORKDIR /workspace
ENV SHELL=/bin/bash
