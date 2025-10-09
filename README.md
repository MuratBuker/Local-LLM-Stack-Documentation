# Local LLM Stack Documentation
  <a href="https://github.com/netbox-community/netbox/stargazers"><img src="https://img.shields.io/github/stars/MuratBuker/Local-LLM-Stack-Documentation?style=flat" alt="GitHub stars" /></a>

Here is a basic diagram of the stack architecture:

![diagram drawio](diagram.drawio.svg)



Linkedin port to read it there. [Article Link](<https://www.linkedin.com/pulse/local-llm-stack-documentation-murat-b%25C3%25BCker-1biuf>)

## Introduction

Especially for enterprise companies, the use of internet-based LLMs raises serious **information security concerns**.

As a result, **local LLM stacks** are becoming increasingly popular as a safer alternative.  

However, many of us — myself included — are not experts in AI or LLMs. During my research, I found that most of the available documentation is either too technical or too high-level, making it difficult to implement a local LLM stack effectively. Also, finding a complete and well-integrated solution can be challenging.

To make this more accessible, I’ve built a **local LLM stack** with open-source components and documented the installation and configuration steps.  

**What does this stack provide**:

* A web-based chat interface to interact with various LLMs.
* Document processing and embedding capabilities.
* Integration with multiple LLM servers for flexibility and performance.
* A vector database for efficient storage and retrieval of embeddings.
* A relational database for storing configurations and chat history.
* MCP servers for enhanced functionalities.
* User authentication and management.
* Web search capabilities for your LLMs.
* Easy management of Docker containers via Portainer.
* GPU support for high-performance computing.
* And more...

---

> ⚠️ **Disclaimer**  
> I am not an expert in this field. The information I share is based solely on my personal experience and research.  
> Please make sure to conduct your own research and thorough testing before applying any of these solutions in a production environment.

---

 The stack is composed of the following components:

* **Portainer**: A web-based management interface for Docker environments. We will use lots containers in this stack, so Portainer will help us manage them easily.

* **Watchtower**: With watchtower you can update the running version of your containerized app simply by pushing a new image to the Docker Hub or your own image registry.

* **Ollama**: A local LLM server that hosts various language models. Not the best performance-wise, but easy to set up and use.

* **vLLM**: A high-performance language model server. It supports a wide range of models and is optimized for speed and efficiency.

* **Open-WebUI**: A web-based user interface for interacting with language models. It supports multiple backends, including Ollama and vLLM.

* **Docling**: A document processing and embedding service. It extracts text from various document formats and generates embeddings for use in LLMs.

* **Searxng**: Open-source Web search engine.

* **MCPO**: A multi-cloud proxy orchestrator that integrates with various MCP servers.

* **Netbox MCP**: MCP server for managing network devices and configurations.

* **Searxng MCP**: MCP for giving Web search capabilities to the model as tool.

* **Time MCP**: A server for providing time-related functionalities.

* **Qdrant**: A vector database for storing and querying embeddings.

* **PostgreSQL**: A relational database for storing configuration and chat history.


---

## Configurations of AI Stack Components

### Pre-note

You can find docker-compose files for each app but also you can see a docker-compose with contains all the stack.

You can experiment with the dedicated yaml files.

### Prerequisites

I will use Ubuntu 24.04 LTS as the operating system for this stack and will install every component on a single server. However, in a production environment, it is recommended to distribute the components across multiple servers for better performance and reliability.

My server is running with NVIDIA RTX 5090 32GB GPU. So, I will install the latest NVIDIA drivers and the NVIDIA Container Toolkit to enable GPU support for the components that require it.

---

### NVIDIA Container Toolkit

Install latest NVIDIA drivers for your GPU

~~~bash
#Example Driver
wget https://us.download.nvidia.com/XFree86/Linux-x86_64/580.82.09/NVIDIA-Linux-x86_64-580.82.09.run
chmod +x NVIDIA-Linux-x86_64-580.82.09.run
sudo ./NVIDIA-Linux-x86_64-580.82.09.run
~~~

Official documentation for installing the NVIDIA Container Toolkit

~~~link
https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
~~~

---

### Portainer Config

I will install Portainer to manage the Docker containers easily via a web interface.

~~~bash
docker volume create portainer_data
docker run -d -p 7000:7000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:lts
~~~

You can login at <https://localhost:9443>.

---

### Context Tester

If you need to calculate what is the maximum context length of a model you can run with your current GPU, you can use MaxContextFinder tool. Not necessary for our stack.

~~~link
https://GitHub.com/Scionero/MaxContextFinder
~~~

~~~bash
maxcontextfinder# python3 main.py my-llama:latest
~~~

---

### Ollama Config

I will run Ollama as a service and increase the default context (2048) length to 32K. You can run Ollama as container as well, but I prefer to run it directly on the host.

* Install Ollama
* Run Ollama as a service
* Increase default context length
* default port 11434

~~~bash
curl -fsSL https://ollama.com/install.sh | sh
~~~

~~~bash
nano /etc/systemd/system/ollama.service
~~~

~~~bash
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin" "OLLAMA_HOST=0.0.0.0" "OLLAMA_CONTEXT_LENGTH=16384" "OLLAMA_NUM_PARALLEL=4" "OLLAMA_MAX_LOADED_MODELS=4"

[Install]
WantedBy=default.target
~~~

Then reload daemon, enable and start service.

~~~bash
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama
~~~

If you want to troubleshoot Ollama you can use:

~~~bash
journalctl -u ollama
~~~

**Some explanation of the parameters:**

**OLLAMA_MAX_LOADED_MODELS=4**: This parameter sets the maximum number of models that can be loaded into memory at the same time. By setting it to 4, you allow up to four models to be active concurrently. This is useful if you plan to work with multiple models and want to switch between them without reloading each time.

**OLLAMA_NUM_PARALLEL=4**: This parameter specifies the number of parallel processing threads that Ollama can use. Setting it to 4 means that Ollama can handle up to four requests simultaneously, which can improve performance when multiple users or applications are accessing the service at the same time.

### Open-WebUI Config

I will use Open-WebUI as the main interface to interact with the language models. It supports both Ollama and vLLM as backends. I will run Open-WebUI as a container using Docker Compose. The simplest docker-compose is below:

~~~bash
mkdir ~/open-webui && cd ~/open-webui
nano docker-compose-file.yaml
~~~

Then copy the below to yaml.

~~~yaml
  open-webui:
    image: ghcr.io/open-webui/open-webui:latest-cuda
    container_name: open-webui
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://localhost:11434
      - ENABLE_OPENAI_API=False
      - WEBUI_NAME=GlassHouse
      - USE_CUDA_DOCKER=True
      - VECTOR_DB=qdrant
      - QDRANT_URI=http://localhost:6333
      - ENABLE_QDRANT_MULTITENANCY_MODE=True
      - CONTENT_EXTRACTION_ENGINE=docling
      - DOCLING_SERVER_URL=http://localhost:5001
      - DOCLING_OCR_ENGINE=tesseract
      - DOCLING_OCR_LANG=eng,tur
      - GLOBAL_LOG_LEVEL=DEBUG
      - RAG_EMBEDDING_ENGINE=ollama
      - RAG_EMBEDDING_MODEL=bge-m3:567m
      - RAG_TOP_K=10
      - RAG_TOP_K_RERANKER=5
      - RAG_EMBEDDING_BATCH_SIZE=30
      - CHUNK_SIZE=2000
      - CHUNK_OVERLAP=200
      - RAG_TEXT_SPLITTER=token
      - ENABLE_CODE_EXECUTION=False
      - ENABLE_WEB_SEARCH=False
      - ENABLE_EVALUATION_ARENA_MODELS=False
      - ENABLE_CODE_INTERPRETER=False
      - DEFAULT_USER_ROLE=pending
      - ENABLE_SIGNUP_PASSWORD_CONFIRMATION=True
      - MCP_ENABLE=True
      - DATABASE_URL=postgresql://openwebui:${DB_PASS}@localhost:5432/openwebui
    network_mode: host
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
~~~

~~~bash
docker-compose up -d
~~~

It will take too long to go over every environment variables. You can check official documentation via [Environment Variables](<https://docs.openwebui.com/getting-started/env-configuration/>).

With default settings, **Open-WebUI** will use **SQLite** as the database to store chat history and configurations and ChromaDB as the vector database to store embeddings.

However, for better performance and scalability, I will use **PostgreSQL** as the database and **Qdrant** as the vector database.

I will run **PostgreSQL** directly on the host, but you can run it as a container as well. So, first install PostgreSQL on the host and create a database and user for Open-WebUI.

~~~bash
sudo apt update
sudo apt install -y postgresql
sudo -u postgres psql
~~~

~~~sql
// CHANGE THE USERNAME AND PASSWORD
CREATE DATABASE openwebui;
CREATE USER openwebui WITH PASSWORD 'openwebui_postgre!!';
ALTER DATABASE openwebui OWNER TO openwebui;
~~~

Now, with below docker-compose file, we can deploy , Open-WebUI with PostgreSQL configuration as the database and Qdrant as Vector DB.

~~~yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:latest-cuda
    container_name: open-webui
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://localhost:11434
      - ENABLE_OPENAI_API=False
      - WEBUI_NAME=GlassHouse
      - USE_CUDA_DOCKER=True
      - VECTOR_DB=qdrant
      - QDRANT_URI=http://localhost:6333
      - ENABLE_QDRANT_MULTITENANCY_MODE=True
      - CONTENT_EXTRACTION_ENGINE=docling
      - DOCLING_SERVER_URL=http://localhost:5001
      - DOCLING_OCR_ENGINE=tesseract
      - DOCLING_OCR_LANG=eng,tur
      - GLOBAL_LOG_LEVEL=DEBUG
      - RAG_EMBEDDING_ENGINE=ollama
      - RAG_EMBEDDING_MODEL=bge-m3:567m
      - RAG_TOP_K=10
      - RAG_TOP_K_RERANKER=5
      - RAG_EMBEDDING_BATCH_SIZE=10
      - CHUNK_SIZE=2000
      - CHUNK_OVERLAP=200
      - RAG_TEXT_SPLITTER=token
      - RAG_EMBEDDING_BATCH_SIZE=30
      - ENABLE_CODE_EXECUTION=False
      - ENABLE_WEB_SEARCH=False
      - SEARXNG_QUERY_URL=http://localhost:4000/search?q=<query>
      - ENABLE_EVALUATION_ARENA_MODELS=False
      - ENABLE_CODE_INTERPRETER=False
      - ENABLE_CODE_EXECUTION=False
      - DEFAULT_USER_ROLE=pending
      - ENABLE_SIGNUP_PASSWORD_CONFIRMATION=True
      - MCP_ENABLE=True
      - DATABASE_URL=postgresql://openwebui:${DB_PASS}@localhost:5432/openwebui

    network_mode: host
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant-storage:/qdrant/storage
    networks:
      - webui-net

volumes:
  open-webui-data:
  qdrant-storage:

networks:
  webui-net:
    name: webui-net
~~~

Because Open-WebUI is heavily developed, it is a good idea to pull the latest image from time to time with below basic steps. Or you can use watchtower which I will talk about later.

* Update open-webui docker image

~~~bash
cd ~/open-webui
docker pull ghcr.io/open-webui/open-webui:latest-cuda
docker rm -f open-webui
docker compose up -d
~~~

---

### SearXNG Config

I will use Searxng as the web search engine for this stack. Searxng is an open-source metasearch engine that aggregates results from various search engines while respecting user privacy.

Why using Searxng and Searxng MCP in this stack? Because, as of right now, Open-WebUI's Web Search feature is lacking performance and reliability. So, I will use Searxng MCP to give web search capabilities to the model as a tool.

You will need settings.yaml file to run Searxng. You can find a sample settings.yaml file below. You can modify it as needed.

~~~bash
mkdir searxng && cd searxng
nano settings.yaml
~~~

Basic settings.yaml file:

~~~yaml
use_default_settings: true

general:
  instance_name: 'searxng'

search:
  autocomplete: 'google'
  formats:
    - html
    - json

server:
  secret_key: 'a2fb23f1b02e6ee83875b09826990de0f6bd908b6638e8c10277d415f6ab852b' # Is overwritten by ${SEARXNG_SECRET}

~~~

Then run create and run docker-compose.yaml file.

docker-compose.yaml >>>

~~~yaml
services:
  searxng:
    image: docker.io/searxng/searxng:latest
    container_name: searxng
    volumes:
      - /~/searxng:/etc/searxng:rw
    ports:
      - 4000:8080
    networks:
      - webui-net
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"

networks:
  webui-net:
    name: webui-net

~~~

---

### Docling Config

If you want to deploy docling separately, you can use below commands.

~~~bash
# Run Docling Serve with GPU support and UI enabled
docker run -d --gpus all -p 5001:5001 -e DOCLING_SERVE_ENABLE_UI=true quay.io/docling-project/docling-serve-cu124
~~~

Or better use below docker-compose file with **CUDA** support.

~~~yaml
services:
  docling-serve:
    image: ghcr.io/docling-project/docling-serve-cu126:main
    container_name: docling-serve
    ports:
      - "5001:5001"
    environment:
      DOCLING_SERVE_ENABLE_UI: "true"
      NVIDIA_VISIBLE_DEVICES: "all"
    runtime: nvidia
    restart: always
~~~

~~~link
http://localhost:5001
~~~

---

### vLLM Config

I will use vLLM as the main LLM inference engine for this stack. vLLM is a high-performance language model server that supports a wide range of models and is optimized for speed and efficiency. Also Ollama does not support reranker models.

**Considerations**:

* vLLM does not support multi model in a single instance. So, for each model, a new instance should be created.

* Every model has model-specific parameters. Please check the vLLM documentation for more details.
* You can create .env file to store environment variables like HF_TOKEN.

Lets first create path and .env.

~~~bash
mkdir ~/vllm && cd ~/vllm
echo "HF_TOKEN=**YOUR_HUGGINGFACE_TOKEN**" > .env
~~~

Then here a sample docker-compose file for vLLM. You can add multiple vLLM services for different models as needed.

~~~yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: vllm
    runtime: nvidia
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    ports:
      - "9001:9001"
    networks:
      - webui-net
    ipc: host
    command: |
      --model BAAI/bge-reranker-v2-m3
      --gpu-memory-utilization 0.8
      --host 0.0.0.0
      --port 9001
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
~~~

---

### MCP Configurations

I will use three different MCP servers for my tests. One is for Netbox, other one is for Web surfing Searxng and the other is for time-date.

LLMs are **not aware** of current **date and time**. So, if you ask a question like "What is the date 10 days from now?", the model will not be able to answer it correctly. To solve this problem, we can use a Time MCP server that provides the current date and time to the model.

In order to run most of the MCP servers, you will need uv. uv is an extremely fast Python package and project manager, written in Rust.

Wİth below command you will install uv with their install script.

~~~bash
wget -qO- https://astral.sh/uv/install.sh | sh
~~~

Netbox MCP GitHub Repo:
<https://GitHub.com/netboxlabs/netbox-mcp-server>

Time MCP GitHub Repo:
<https://GitHub.com/modelcontextprotocol/servers/tree/main/src/time>

Searxng MCP GitHub Repo:
<https://github.com/ihor-sokoliuk/mcp-searxng>

If you want you can add Wikipedia MCP as well.

I will use MCPO to proxy all the MCP servers. MCPO is a multi-cloud proxy orchestrator that can manage multiple MCP servers.

### MCPO Config

* GitHub Repo: <https://GitHub.com/open-webui/mcpo>
* Create a config file for MCP servers
* Run MCPO as a service via port 8009 (whatever port you want)

~~~bash
mkdir /~~/mcpo
pip install mcpo
nano /~~/mcpo/config.json
~~~

Copy-paste below json to file.
  
~~~json
{
  "mcpServers": {

    "netbox": {
      "command": "/root/.local/bin/uv",
      "args": [
        "--directory",
        "/root/netbox-mcp-server",
        "run",
        "server.py"
      ],
      "env": {
        "NETBOX_URL": "https://localhost/",
        "NETBOX_TOKEN": "e76baad4fa637b6c3c597cdcb691a69abf61ab44"
      }
    },

    "time": {
      "command": "/root/.local/bin/uvx",
      "args": [
        "mcp-server-time"
      ]
    },

    "searxng": {
      "command": "npx",
      "args": [
        "--y",
        "mcp-searxng"
      ],
      "env": {
        "SEARXNG_URL": "http://localhost:4000"
      }
    },

    "wikipedia": {
      "command": "/root/wiki-mcp/venv/bin/wikipedia-mcp",
      "args": ["--country", "TR"]
    }
  }
}
~~~

In order to run MCPO as a linux service do the below steps:

~~~bash
nano /etc/systemd/system/mcpo.service
~~~

~~~text
[Unit]
Description=My Custom Proxy Orchestrator
After=network.target

[Service]
User=root
Group=root
ExecStart=/root/.local/bin/uvx mcpo --port 8009 --config /root/mcpo/config.json
WorkingDirectory=/root/mcpo
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
~~~

Then reload daemon, enable and start service.

~~~bash
systemctl daemon-reload
systemctl enable mcpo
systemctl start mcpo
~~~

If you want to check for service logs, you can use follow:

~~~bash
journalctl -u mcpo
~~~

---

### Watchtower

Since we are heavily using Docker container, managing their image updates is a thing. You can use Watchtower to monitor and check every container you specified at the defined time. It will download new image if any and restart the container with the new image.

You can use below docker-compose. You can add or remove container names.

~~~yaml
services:
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - TZ=Europe/Istanbul #your timezone
    command: --schedule "0 0 0 * * *" open-webui docling-serve searxng portainer
~~~

---

### Bundled Stack Docker Compose

And finally one big docker-compose file to deploy all the containers we discussed. Do not forget to create **.env** file with Huggingface token.

~~~yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:latest-cuda
    container_name: open-webui
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://localhost:11434
      - ENABLE_OPENAI_API=True
      - OPENAI_API_BASE_URL=http://localhost:9002/v1
      - WEBUI_NAME=GlassHouse
      - USE_CUDA_DOCKER=True
      - VECTOR_DB=qdrant
      - QDRANT_URI=http://localhost:6333
      - ENABLE_QDRANT_MULTITENANCY_MODE=True
      - CONTENT_EXTRACTION_ENGINE=docling
      - DOCLING_SERVER_URL=http://localhost:5001
      - DOCLING_OCR_ENGINE=tesseract
      - DOCLING_OCR_LANG=eng,tur
      - GLOBAL_LOG_LEVEL=DEBUG
      - RAG_EMBEDDING_ENGINE=ollama
      - RAG_EMBEDDING_MODEL=bge-m3:567m
      - RAG_TOP_K=10
      - RAG_TOP_K_RERANKER=5
      - RAG_EMBEDDING_BATCH_SIZE=100
      - CHUNK_SIZE=2000
      - CHUNK_OVERLAP=200
      - RAG_TEXT_SPLITTER=token
      - RAG_RERANKING_MODEL=Qwen/Qwen3-Reranker-0.6B
      - ENABLE_CODE_EXECUTION=False
      - ENABLE_WEB_SEARCH=False
      - ENABLE_EVALUATION_ARENA_MODELS=False
      - ENABLE_CODE_INTERPRETER=False
      - DEFAULT_USER_ROLE=pending
      - ENABLE_SIGNUP_PASSWORD_CONFIRMATION=True
      - MCP_ENABLE=True
      - DATABASE_URL=postgresql://openwebui:${DB_PASS}@localhost:5432/openwebui
    network_mode: host
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
    volumes:
      - qdrant-storage:/qdrant/storage
    networks:
      - webui-net

  docling-serve:
    image: ghcr.io/docling-project/docling-serve-cu128:main
    container_name: docling-serve
    ports:
      - "5001:5001"
    environment:
      DOCLING_SERVE_MAX_SYNC_WAIT: 720
      DOCLING_SERVE_ENABLE_UI: "true"
      NVIDIA_VISIBLE_DEVICES: "all"
    runtime: nvidia
    restart: unless-stopped
    networks:
      - webui-net

  vllm-Qwen3-Reranker-06B:
    image: vllm/vllm-openai:v0.10.2
    container_name: vllm-Qwen3-Reranker-06B
    runtime: nvidia
    restart: unless-stopped
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    ports:
      - "9001:9001"
    networks:
      - webui-net
    ipc: host
    command: |
      --model Qwen/Qwen3-Reranker-0.6B
      --gpu-memory-utilization 0.22
      --host 0.0.0.0
      --port 9001
      --max-model-len 16000
      --cpu-offload-gb 10
      --hf_overrides '{"architectures": ["Qwen3ForSequenceClassification"],"classifier_from_token": ["no", "yes"],"is_original_qwen3_reranker": true}'  
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  vllm-gpt:
    image: vllm/vllm-openai:v0.10.2
    container_name: vllm-gpt
    runtime: nvidia
    restart: unless-stopped
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ~/.cache/huggingface:/root/.cache/huggingface
    ports:
      - "9002:9002"
    networks:
      - webui-net
    ipc: host
    command: |
      --model openai/gpt-oss-20b
      --gpu-memory-utilization 0.6
      --host 0.0.0.0
      --port 9002
      --max-model-len 32000
      --max-num-seqs 128
      --async-scheduling
      --api-key 123456
      --enable-auto-tool-choice
      --tool-call-parser openai
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - TZ=Europe/Istanbul
    command: --schedule "0 0 0 * * *" open-webui docling-serve searxng portainer

  searxng:
    image: docker.io/searxng/searxng:latest
    container_name: searxng
    volumes:
      - /~/searxng:/etc/searxng:rw
    ports:
      - 4000:8080
    networks:
      - webui-net
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"

volumes:
  open-webui-data:
  qdrant-storage:

networks:
  webui-net:
    name: webui-net
~~~

---

### Closing

Thank you for reading till here : )

If you have any questions or need further assistance, feel free to reach out. I hope this documentation helps you set up your own local LLM stack successfully!

Take care.

Murat - 30.10.2025
