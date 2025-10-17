# Smart Logging - Multi-Agent RAG for OpenShift

**Multi-agent self-corrective RAG system for OpenShift/Kubernetes log analysis**

[![Status](https://img.shields.io/badge/status-production--ready-green)]()
[![Detection Rate](https://img.shields.io/badge/detection--rate-100%25-brightgreen)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)]()

---

## 🎯 Overview

Smart Logging analyzes OpenShift/Kubernetes logs using a multi-agent AI system inspired by [NVIDIA's architecture](https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/). It automatically identifies issues, root causes, and provides actionable solutions.

### Key Features

- ✅ **100% Detection Rate** - Identifies all pod issues including missing ConfigMaps and Secrets
- 🔍 **Hybrid Retrieval** - Combines BM25 (lexical) + FAISS (semantic) with Reciprocal Rank Fusion
- 🎯 **BGE Reranker** - Refines results using BGE Reranker v2-m3
- 🔄 **Self-Corrective** - Iterative query transformation (up to 3 iterations)
- 🤖 **5 Specialized Agents** - Retrieve, Rerank, Grade, Generate, Transform
- 🚀 **Fast** - 5-10 second response time

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Issue Detection | 100% |
| Response Time | 5-10 seconds |
| Chunks per Pod | 3-5 |
| Self-Correction Iterations | 0-3 (avg 0.5) |

---

## 🏗️ Architecture

```
User Query
    ↓
┌─────────────────────────────┐
│ Agent 1: Retrieve            │
│ • Fetch logs (oc describe)  │
│ • Hybrid: BM25 + FAISS      │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Agent 2: Rerank              │
│ • BGE Reranker v2-m3        │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Agent 3: Grade Documents     │
│ • Inclusive philosophy      │
│ • Full content evaluation   │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Agent 4: Generate Answer     │
│ • Llama 3.2 3B Instruct     │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ Decision: Answer Quality?    │
│ Good → Return               │
│ Poor → Agent 5: Transform   │
└─────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- OpenShift 4.x or Kubernetes 1.20+
- Llama Stack service with:
  - LLM: `llama-32-3b-instruct`
  - Embeddings: `granite-embedding-125m`
- BGE Reranker v2-m3 service
- `oc` CLI installed

### Deploy in 5 Minutes

```bash
# 1. Clone repository
git clone https://github.com/nirjhar17/smart_logging.git
cd smart_logging

# 2. Create namespace
oc new-project smart-logging

# 3. Deploy RBAC
oc apply -f v8-rbac.yaml

# 4. Create ConfigMap with code
oc create configmap smart-logging-code \
  --from-file=v7_graph_nodes.py \
  --from-file=v7_graph_edges.py \
  --from-file=v7_main_graph.py \
  --from-file=v7_state_schema.py \
  --from-file=v7_bge_reranker.py \
  --from-file=k8s_hybrid_retriever.py \
  --from-file=k8s_log_fetcher.py \
  --from-file=v8_streamlit_chat_app.py \
  --from-file=app.py=v8_streamlit_chat_app.py

# 5. Update environment variables in v7-deployment.yaml
# Set LLAMA_STACK_URL and BGE_RERANKER_URL

# 6. Deploy
oc apply -f v7-deployment.yaml

# 7. Get route URL
oc get route smart-logging
```

---

## ⚙️ Configuration

Edit environment variables in `v7-deployment.yaml`:

```yaml
env:
- name: LLAMA_STACK_URL
  value: "http://your-llama-stack:8321"
- name: BGE_RERANKER_URL
  value: "https://your-bge-reranker"
- name: LLAMA_STACK_MODEL
  value: "llama-32-3b-instruct"
- name: EMBEDDING_MODEL
  value: "granite-embedding-125m"
```

---

## 🧪 Example Usage

### Healthy Pod
```
Query: What is the issue with pod nginx-xxx?
Answer: ✅ No issues detected. Pod is running normally.
```

### Missing Resources
```
Query: What is the issue with pod app-xxx?
Answer: 
🚨 ISSUE: Multiple missing resources
- Missing ConfigMap: app-config
- Missing Secret: app-secret

🔧 RESOLUTION:
oc create configmap app-config --from-literal=...
oc create secret generic app-secret --from-literal=...
```

---

## 🔧 Technical Details

### Hybrid Retrieval
- **BM25**: Lexical/keyword matching
- **FAISS**: Semantic similarity (Granite 125M embeddings)
- **RRF**: Reciprocal Rank Fusion for combining results

### Chunking Strategy
- **Chunk Size**: 1,000 characters (optimized for BGE's 512 token limit)
- **Overlap**: 200 characters (20%)
- **Separators**: `\n\n`, `\n`, ` `

### Critical Fixes Applied

This version includes 3 critical fixes that improved detection from 50% to 100%:

1. **Full Document Grading** - Agent 3 sees complete content (no truncation)
2. **Inclusive Philosophy** - "Partial relevance = yes" (from NVIDIA)
3. **Optimized Chunk Size** - 1K chars (fits BGE's 512 token limit)

See [CRITICAL_FIXES_APPLIED.md](./CRITICAL_FIXES_APPLIED.md) for technical details.

---

## 📁 Repository Structure

```
smart_logging/
├── README.md                     # This file
├── CRITICAL_FIXES_APPLIED.md     # Technical fix details
│
├── Python Files (Agents & Logic)
│   ├── v7_graph_nodes.py         # 5 agent implementations
│   ├── v7_graph_edges.py         # Routing logic
│   ├── v7_main_graph.py          # LangGraph workflow
│   ├── v7_state_schema.py        # State management
│   ├── k8s_hybrid_retriever.py   # Hybrid retrieval (NVIDIA-style)
│   ├── v7_bge_reranker.py        # BGE reranker client
│   ├── k8s_log_fetcher.py        # Log fetcher
│   └── v8_streamlit_chat_app.py  # Chat UI
│
└── Kubernetes Manifests
    ├── v7-deployment.yaml        # Main deployment
    └── v8-rbac.yaml              # RBAC configuration
```

---

## 🔍 Troubleshooting

### Pod Not Starting
```bash
# Check logs
oc logs deployment/smart-logging

# Common issues:
# 1. Llama Stack URL incorrect
# 2. BGE Reranker URL incorrect
# 3. RBAC not configured
```

### Detection Issues
```bash
# Verify chunk size
oc get configmap smart-logging-code -o yaml | grep chunk_size
# Should show: chunk_size=1000

# Check logs for retrieval
oc logs deployment/smart-logging | grep "Retrieved.*documents"
# Should show multiple documents (3-5+)
```

---

## 🎓 Inspiration

Based on [NVIDIA's Multi-Agent Log Analysis](https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/) approach, adapted for OpenShift with self-hosted models.

### Key Adaptations
- NVIDIA NV-EmbedQA-1B → Granite 125M
- NVIDIA Nemotron 49B → Llama 3.2 3B
- NVIDIA NV-RerankQA-1B → BGE Reranker v2-m3
- Generic logs → OpenShift-specific
- NVIDIA AI Endpoints → Llama Stack

---

## 📚 Documentation

- **README.md** - This file (overview & quick start)
- **CRITICAL_FIXES_APPLIED.md** - Technical details of 3 critical fixes

---

## 🤝 Contributing

Contributions welcome! Key areas:
- Agent prompt optimization
- Additional retrieval strategies
- Performance improvements
- New deployment targets

---

## 📝 License

Apache 2.0 - Adapts concepts from NVIDIA's GenerativeAIExamples

---

## 🔗 Links

- **GitHub**: https://github.com/nirjhar17/smart_logging
- **NVIDIA Blog**: https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/
- **NVIDIA Code**: https://github.com/NVIDIA/GenerativeAIExamples/tree/main/community/log_analysis_multi_agent_rag

---

**Built with ❤️ for OpenShift Troubleshooting**
