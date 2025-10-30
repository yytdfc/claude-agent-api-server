# Use Node.js Trixie as base image
FROM node:trixie-slim

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

RUN apt update && \
    apt install -y curl git git-lfs wget gh && \
    npm install -g @anthropic-ai/claude-code && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mkdir /workspace
    # uv venv /root/.venv && \
    # echo "export VIRTUAL_ENV_DISABLE_PROMPT=1" >> /root/.bashrc && \
    # echo "source /app/.venv/bin/activate" >> /root/.bashrc && \
    # echo "export PS1='\w $ '" >> /root/.bashrc && \
    # . /root/.venv/bin/activate && \
    # uv pip install pip && \

# Install Python dependencies using uv

# RUN echo hello

COPY . /app/

# Set working directory
WORKDIR /app


RUN mv /app/docker/CLAUDE.md /workspace && \
    echo "export VIRTUAL_ENV_DISABLE_PROMPT=1" >> /root/.bashrc && \
    echo "source /app/.venv/bin/activate" >> /root/.bashrc
    # cd /app; ln -s /root/.venv .venv
    # uv sync && \
    # git clone https://github.com/yytdfc/claude-agent-api-server.git && \
    # cd claude-agent-api-server && \

# Expose port 8080
EXPOSE 8080

# Run the server on port 8080
CMD ["/app/serve"]
