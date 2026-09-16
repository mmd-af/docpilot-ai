FROM node:24-bookworm

RUN apt-get update && \
    apt-get install -y python3 python3-pip curl git sudo && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages --no-cache-dir uv

WORKDIR /workspace/docpilot-ai

CMD ["bash"]