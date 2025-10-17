# 📦 AI Troubleshooter v7 - Component Architecture

**Project:** OpenShift Log Analysis Multi-Agent Self-Corrective RAG System  
**Version:** 7.0  
**Last Updated:** October 15, 2025

---

## 🎯 Overview

This document maps all components of the v7 multi-agent system, their files, purposes, and relationships. Inspired by NVIDIA's log analysis architecture but adapted for OpenShift with Llama Stack.

---

## 📊 Core Components Table

| Component | File | Purpose | NVIDIA Equivalent |
|-----------|------|---------|-------------------|
| **StateGraph** | `v7_main_graph.py` | Defines the LangGraph workflow orchestration | `bat_ai.py` |
| **Nodes (Agents)** | `v7_graph_nodes.py` | Implements 5 specialized agents (retrieve, rerank, grade, generate, transform) | `graphnodes.py` |
| **Edges (Routing)** | `v7_graph_edges.py` | Encodes conditional transitions and self-correction logic | `graphedges.py` |
| **Hybrid Retriever** | `v7_hybrid_retriever.py` | Combines BM25 (lexical) + Milvus (semantic) retrieval | `multiagent.py` |
| **State Schema** | `v7_state_schema.py` | Defines GraphState (shared memory across agents) | Inline in `bat_ai.py` |
| **Log Collector** | `v7_log_collector.py` | OpenShift data collection (pods, logs, events, metrics) | N/A (NVIDIA uses static files) |
| **Frontend UI** | `v7_streamlit_app.py` | Streamlit web interface for user interaction | `example.py` |
| **Dependencies** | `v7_requirements.txt` | Python package dependencies | `requirements.txt` |
| **Deployment** | `v7-deployment.yaml` | Kubernetes Deployment manifest | N/A |
| **RBAC** | `v7-rbac.yaml` | ServiceAccount, ClusterRole, ClusterRoleBinding | N/A |
| **Environment** | `.env.v7` | Environment variables configuration | N/A |

---

## 🔍 Detailed Component Breakdown

### 1. **StateGraph** (`v7_main_graph.py`)

**Purpose:** Orchestrates the multi-agent workflow using LangGraph

**Key Functions:**
- `create_workflow()`: Builds the directed graph with nodes and edges
- `run_analysis()`: Executes the workflow for a given query

**Key Nodes:**
```python
workflow.add_node("retrieve", nodes.retrieve)
workflow.add_node("rerank", nodes.rerank)
workflow.add_node("grade_documents", nodes.grade_documents)
workflow.add_node("generate", nodes.generate)
workflow.add_node("transform_query", nodes.transform_query)
```

**Conditional Edges:**
- After grading: → Generate OR Transform Query
- After generation: → END OR Transform Query (self-correction)

**Lines of Code:** ~130  
**Dependencies:** `langgraph`, `graph_nodes`, `graph_edges`, `state_schema`

---

### 2. **Nodes (Agents)** (`v7_graph_nodes.py`)

**Purpose:** Implements each specialized agent in the workflow

**Class:** `Nodes`

**Agent 1: `retrieve()`** [Lines 39-95]
- **Task:** Hybrid retrieval using BM25 + Milvus
- **Input:** Question, log context, pod events
- **Output:** Top 10 retrieved documents
- **Key Logic:**
  - Builds BM25 index from logs
  - Enhances query with context keywords
  - Performs hybrid retrieval

**Agent 2: `rerank()`** [Lines 97-143]
- **Task:** Reranks documents by relevance score
- **Input:** Retrieved documents
- **Output:** Top 5 reranked documents
- **Note:** Currently uses score sorting; can be upgraded to BGE reranker

**Agent 3: `grade_documents()`** [Lines 145-221]
- **Task:** LLM-based relevance grading
- **Input:** Reranked documents + question
- **Output:** Filtered relevant documents
- **LLM Call:** Yes (Llama 3.2 3B)
- **Prompt:** Asks "Is this log snippet relevant?"

**Agent 4: `generate()`** [Lines 223-307]
- **Task:** Generates structured troubleshooting answer
- **Input:** Filtered documents + question
- **Output:** Formatted diagnosis with root cause & actions
- **LLM Call:** Yes (Llama 3.2 3B)
- **Prompt:** System prompt for OpenShift SRE analysis

**Agent 5: `transform_query()`** [Lines 309-369]
- **Task:** Rewrites query for better retrieval (self-correction)
- **Input:** Original question, iteration count
- **Output:** Transformed query
- **LLM Call:** Yes (Llama 3.2 3B)
- **Tracks:** Transformation history

**Lines of Code:** ~418  
**Dependencies:** `LlamaStackClient`, `HybridRetriever`, `GraphState`

---

### 3. **Edges (Routing Logic)** (`v7_graph_edges.py`)

**Purpose:** Implements conditional routing for self-correction

**Class:** `Edge`

**Decision 1: `decide_to_generate()`** [Lines 17-72]
- **When:** After document grading
- **Logic:**
  - No relevant docs + iterations < 3 → `transform_query`
  - Good docs OR max iterations → `generate`
- **Checks:** Document count, relevance scores, iteration count

**Decision 2: `grade_generation_vs_documents_and_question()`** [Lines 75-136]
- **When:** After answer generation
- **Logic:**
  - Answer useful + supported → `END`
  - Answer not useful + iterations < 3 → `transform_query`
  - Max iterations → `END` (accept answer)
- **Method:** Heuristic checks (keyword overlap, length, doc support)

**Lines of Code:** ~189  
**Dependencies:** `GraphState`, `Literal`

---

### 4. **Hybrid Retriever** (`v7_hybrid_retriever.py`)

**Purpose:** Combines BM25 (lexical) + Milvus (semantic) retrieval

**Class:** `HybridRetriever`

**Key Methods:**

**`build_bm25_index()`** [Lines 46-71]
- Builds in-memory BM25 index from log documents
- Tokenizes log lines for keyword matching

**`retrieve_bm25()`** [Lines 84-124]
- Performs keyword-based retrieval
- Returns top-k documents with BM25 scores

**`retrieve_vector()`** [Lines 126-160]
- Performs semantic search via Llama Stack + Milvus
- Uses granite-embedding-125m for embeddings

**`hybrid_retrieve()`** [Lines 162-188]
- Combines BM25 and vector results
- Uses Reciprocal Rank Fusion (RRF) for score merging
- Alpha = 0.5 (equal weight to both methods)

**`_reciprocal_rank_fusion()`** [Lines 190-253]
- Implements RRF algorithm
- Formula: `score = Σ(1 / (k + rank))`
- Handles duplicate documents from both sources

**Lines of Code:** ~299  
**Dependencies:** `rank-bm25`, `LlamaStackClient`, `re`

---

### 5. **State Schema** (`v7_state_schema.py`)

**Purpose:** Defines the shared state (GraphState) passed between agents

**TypedDict:** `GraphState`

**State Fields:**

**Input:**
- `question`: User's query
- `namespace`: OpenShift namespace
- `pod_name`: Target pod (optional)
- `time_window`: Log collection window (minutes)

**Log Context:**
- `log_context`: Raw pod logs (100 lines)
- `pod_events`: Kubernetes events
- `pod_status`: Pod status JSON

**Retrieval:**
- `retrieved_docs`: Documents from hybrid retrieval
- `reranked_docs`: Top documents after reranking
- `relevance_scores`: Scores from grading

**Generation:**
- `generation`: Final LLM-generated answer

**Self-Correction:**
- `iteration`: Current iteration count
- `max_iterations`: Maximum retries (default: 3)
- `transformation_history`: List of query transformations

**Metadata:**
- `timestamp`: Analysis start time
- `data_source`: MCP or oc commands

**Lines of Code:** ~99  
**Dependencies:** `typing`, `typing_extensions`

---

### 6. **Log Collector** (`v7_log_collector.py`)

**Purpose:** Collects logs, events, and metrics from OpenShift

**Class:** `KubernetesDataCollector`

**Key Methods:**

**`get_namespaces()`**
- Lists all namespaces via `oc get namespaces`

**`get_pods(namespace)`**
- Lists pods in a namespace

**`get_pod_logs(pod_name, namespace, lines=100)`**
- Fetches pod logs (last N lines)

**`get_pod_events(namespace)`**
- Gets Kubernetes events for troubleshooting

**`get_pod_info(pod_name, namespace)`**
- Retrieves pod JSON spec and status

**Functions:**

**`ingest_openshift_docs_v7()`**
- Ingests OpenShift documentation into Milvus
- Chunks PDFs and creates embeddings

**Lines of Code:** ~350 (estimated)  
**Dependencies:** `subprocess`, `LlamaStackClient`

---

### 7. **Frontend UI** (`v7_streamlit_app.py`)

**Purpose:** Streamlit web interface for user interaction

**Key Features:**
- Namespace selector
- Pod selector (filtered by namespace)
- Question input
- Multi-agent deep analysis button
- Progress indicators
- Real-time log streaming
- Result display with metadata

**Workflow Integration:**
- Calls `create_workflow()` and `run_analysis()`
- Displays GraphState at each step
- Shows iteration count and transformations

**UI Sections:**
1. Sidebar: Namespace/pod selection, settings
2. Main area: Question input, results
3. Expanders: Raw logs, pod events, pod status

**Lines of Code:** ~400 (estimated)  
**Dependencies:** `streamlit`, `v7_main_graph`, `v7_log_collector`

---

### 8. **Dependencies** (`v7_requirements.txt`)

**Purpose:** Lists all Python package dependencies

**Key Packages:**

**LLM & RAG:**
- `llama-stack-client>=0.0.53`
- `langgraph>=0.2.45`
- `langgraph-checkpoint>=2.0.2`

**Retrieval:**
- `rank-bm25>=0.2.2`
- `sentence-transformers>=2.2.0` (optional, for BGE reranker)

**Frontend:**
- `streamlit>=1.28.0`

**Utilities:**
- `python-dotenv>=1.0.0`
- `requests>=2.31.0`

**Total Packages:** 40

---

### 9. **Deployment Manifests**

#### `v7-deployment.yaml`
**Purpose:** Kubernetes Deployment for v7 app

**Key Specs:**
- Image: `registry.access.redhat.com/ubi9/python-311:latest`
- Resources: 2 CPU, 4Gi memory
- Environment variables from `.env.v7`
- Installs `oc` client at runtime
- Mounts ConfigMap with Python files
- Service: ClusterIP on port 8501
- Route: HTTPS with edge termination

**Lines:** ~150

#### `v7-rbac.yaml`
**Purpose:** RBAC permissions for OpenShift access

**Components:**
- `ServiceAccount`: `ai-troubleshooter-v7-sa`
- `ClusterRole`: Read access to pods, logs, events, namespaces
- `ClusterRoleBinding`: Links SA to role

**Permissions:**
- `get`, `list`, `watch` on:
  - pods, pods/log
  - events
  - namespaces
  - deployments, replicasets
  - services, routes
  - persistentvolumeclaims

**Lines:** ~50

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User (Streamlit UI)                      │
│                      v7_streamlit_app.py                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓ (User query + namespace + pod)
┌─────────────────────────────────────────────────────────────────┐
│                    Log Collector (v7_log_collector.py)           │
│  - Fetches pod logs (oc logs)                                   │
│  - Fetches events (oc get events)                               │
│  - Fetches pod status (oc get pod -o json)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓ (log_context, pod_events, pod_status)
┌─────────────────────────────────────────────────────────────────┐
│              StateGraph Workflow (v7_main_graph.py)              │
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐           │
│  │  RETRIEVE  │───▶│   RERANK   │───▶│    GRADE   │           │
│  └────────────┘    └────────────┘    └──────┬─────┘           │
│        │ (uses v7_hybrid_retriever.py)       │                 │
│        │                                      ↓                 │
│        │                          ┌───────────────────┐        │
│        │                          │   DECISION 1:     │        │
│        │                          │  Good docs?       │        │
│        │                          └─────┬─────┬───────┘        │
│        │                                │     │                │
│        │                               YES   NO                │
│        │                                │     │                │
│        │                                ↓     ↓                │
│        │                          ┌──────────┐ ┌──────────┐   │
│        │                          │ GENERATE │ │TRANSFORM │   │
│        │                          └────┬─────┘ │  QUERY   │   │
│        │                               │       └────┬─────┘   │
│        │                               ↓            │         │
│        │                          ┌───────────────┐ │         │
│        │                          │  DECISION 2:  │ │         │
│        │                          │ Answer good?  │ │         │
│        │                          └─────┬─────┬───┘ │         │
│        │                                │     │     │         │
│        │                               YES   NO     │         │
│        │                                │     │     │         │
│        │                                ↓     └─────┘         │
│        │                              [END]         │         │
│        │                                            │         │
│        └────────────────────────────────────────────┘         │
│                     (Loop back: max 3 iterations)              │
│                                                                │
│  All agents in v7_graph_nodes.py                              │
│  Routing logic in v7_graph_edges.py                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ↓ (final answer)
┌─────────────────────────────────────────────────────────────────┐
│                      Display Results (Streamlit)                 │
│  - Formatted answer (Issue, Root Cause, Actions, Resolution)    │
│  - Metadata (model, iteration, evidence count)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Component Interactions

### Agent Communication (via GraphState)

```python
# Agent 1 (Retrieve) produces:
{
    "retrieved_docs": [...],  # Top 10 docs
}

# Agent 2 (Rerank) consumes & produces:
{
    "retrieved_docs": [...],   # Input
    "reranked_docs": [...]     # Output (Top 5)
}

# Agent 3 (Grade) consumes & produces:
{
    "reranked_docs": [...],        # Input
    "reranked_docs": [...],        # Output (filtered)
    "relevance_scores": [1.0, 1.0] # Output
}

# Agent 4 (Generate) consumes & produces:
{
    "reranked_docs": [...],   # Input
    "question": "...",        # Input
    "generation": "..."       # Output (answer)
}

# Agent 5 (Transform) consumes & produces:
{
    "question": "old query",           # Input
    "question": "optimized query",     # Output (replaces)
    "iteration": 2,                    # Output
    "transformation_history": [...]    # Output
}
```

---

## 🔧 External Dependencies

### Llama Stack Services

```
┌─────────────────────────────────────────────────────────┐
│  Llama Stack (llamastack-custom-distribution)           │
│  http://llamastack-custom-distribution-service          │
│         .model.svc.cluster.local:8321                   │
├─────────────────────────────────────────────────────────┤
│  Providers:                                             │
│  - Inference: llama-32-3b-instruct (vLLM)              │
│  - Embeddings: granite-embedding-125m                   │
│  - Vector DB: Milvus (inline)                          │
│  - Tool Runtime: RAG, MCP                              │
└─────────────────────────────────────────────────────────┘
```

### OpenShift Resources

```
┌─────────────────────────────────────────────────────────┐
│  OpenShift Cluster                                      │
├─────────────────────────────────────────────────────────┤
│  Accessed via:                                          │
│  - oc CLI (installed in container)                     │
│  - ServiceAccount: ai-troubleshooter-v7-sa             │
│                                                         │
│  Resources read:                                        │
│  - Namespaces                                          │
│  - Pods (status, logs, events)                        │
│  - Deployments, ReplicaSets                           │
│  - Services, Routes                                    │
│  - PersistentVolumeClaims                             │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Comparison: Our V7 vs NVIDIA

| Component | NVIDIA | Our V7 | Status |
|-----------|--------|--------|--------|
| **StateGraph** | `bat_ai.py` | `v7_main_graph.py` | ✅ Same concept |
| **Agents/Nodes** | `graphnodes.py` | `v7_graph_nodes.py` | ✅ Same structure |
| **Routing/Edges** | `graphedges.py` | `v7_graph_edges.py` | ✅ Same logic |
| **Hybrid Retrieval** | `multiagent.py` (BM25+FAISS) | `v7_hybrid_retriever.py` (BM25+Milvus) | ✅ Same approach |
| **Output Models** | `binary_score_models.py` | Inline in `GraphState` | ⚠️ Different format |
| **Prompts** | `prompt.json` | Inline in node functions | ⚠️ Different storage |
| **Data Source** | Static log files | Live OpenShift (oc CLI) | 🚀 Enhanced |
| **UI** | `example.py` (basic) | `v7_streamlit_app.py` (rich) | 🚀 Enhanced |
| **Main LLM** | Nemotron 49B | Llama 3.2 3B | ⚠️ Smaller model |
| **Embeddings** | llama-3.2-nv-embedqa (1B) | granite-125m | ✅ Similar |
| **Reranker** | llama-3.2-nv-rerankqa (1B) | Score sorting (upgradable to BGE) | ⚠️ Can improve |

---

## 🗂️ File Organization

```
ai-troubleshooter-v7/
├── Core Workflow
│   ├── v7_main_graph.py          (StateGraph orchestration)
│   ├── v7_graph_nodes.py         (Agent implementations)
│   ├── v7_graph_edges.py         (Conditional routing)
│   └── v7_state_schema.py        (GraphState definition)
│
├── RAG Components
│   ├── v7_hybrid_retriever.py    (BM25 + Milvus)
│   └── v7_log_collector.py       (Data ingestion)
│
├── User Interface
│   └── v7_streamlit_app.py       (Streamlit app)
│
├── Configuration
│   ├── v7_requirements.txt       (Python deps)
│   └── .env.v7                   (Environment vars)
│
├── Deployment
│   ├── v7-deployment.yaml        (K8s Deployment)
│   └── v7-rbac.yaml              (ServiceAccount + RBAC)
│
└── Documentation
    ├── ARCHITECTURE_DIAGRAM.md   (Visual diagrams)
    ├── COMPLETE_V7_GUIDE.md      (Comprehensive guide)
    ├── COMPONENTS.md             (This file)
    ├── FAQ_GUIDE.md              (Q&A)
    ├── QUICK_REFERENCE.md        (Cheat sheet)
    ├── DEPLOYMENT_CHECKLIST.md   (Deploy guide)
    └── PROJECT_SUMMARY.md        (Executive summary)
```

---

## 🚀 Getting Started

### 1. Review Key Files (Recommended Order)

```bash
# Start here
1. v7_state_schema.py       # Understand data structure
2. v7_graph_nodes.py        # See agent implementations
3. v7_graph_edges.py        # Understand routing logic
4. v7_main_graph.py         # See workflow assembly
5. v7_streamlit_app.py      # Explore UI integration
```

### 2. Trace a Request

```python
# Follow this path through the code:

1. User enters question in Streamlit UI
   → v7_streamlit_app.py: st.text_input()

2. Collect logs
   → v7_log_collector.py: KubernetesDataCollector.get_pod_logs()

3. Create workflow
   → v7_main_graph.py: create_workflow()

4. Run analysis
   → v7_main_graph.py: run_analysis()
   → Enters StateGraph

5. Agent 1: Retrieve
   → v7_graph_nodes.py: Nodes.retrieve()
   → v7_hybrid_retriever.py: HybridRetriever.hybrid_retrieve()

6. Agent 2: Rerank
   → v7_graph_nodes.py: Nodes.rerank()

7. Agent 3: Grade
   → v7_graph_nodes.py: Nodes.grade_documents()
   → LLM call to Llama 3.2 3B

8. Decision 1: Generate or Transform?
   → v7_graph_edges.py: Edge.decide_to_generate()

9. Agent 4: Generate
   → v7_graph_nodes.py: Nodes.generate()
   → LLM call to Llama 3.2 3B

10. Decision 2: Answer good?
    → v7_graph_edges.py: Edge.grade_generation_vs_documents_and_question()

11. Return to UI
    → v7_streamlit_app.py: Display result
```

---

## 📈 Future Component Enhancements

### Planned Upgrades

1. **Enhanced Reranker** (`v7_graph_nodes.py`)
   - Upgrade from score sorting to BGE reranker model
   - Add `sentence-transformers` integration

2. **LLM-Based Validation** (`v7_graph_edges.py`)
   - Replace heuristic checks with LLM call
   - More accurate quality assessment

3. **Metrics Collection** (`v7_log_collector.py`)
   - Add `get_pod_metrics()` method
   - Include `oc adm top pod` output

4. **Prompt Library** (New: `v7_prompts.py`)
   - Externalize prompts from node functions
   - Version control and A/B testing

5. **ServiceNow Integration** (New: `v7_servicenow_connector.py`)
   - Fetch resolution history from tickets
   - Add to RAG knowledge base

---

## 🎯 Key Metrics

| Metric | Value |
|--------|-------|
| **Total Python Files** | 8 core files |
| **Total Lines of Code** | ~2,000 |
| **Agents/Nodes** | 5 |
| **Decision Points** | 2 (self-correction) |
| **LLM Calls per Query** | 3-9 (depends on iterations) |
| **Max Iterations** | 3 |
| **Average Response Time** | 10-20 seconds |
| **Dependencies** | 40 packages |

---

## 📚 Related Documentation

- **[ARCHITECTURE_DIAGRAM.md](./ARCHITECTURE_DIAGRAM.md)** - Visual diagrams
- **[COMPLETE_V7_GUIDE.md](./COMPLETE_V7_GUIDE.md)** - Full implementation guide
- **[FAQ_GUIDE.md](./FAQ_GUIDE.md)** - Frequently asked questions
- **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Deployment steps
- **[PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)** - Executive overview

---

**Last Updated:** October 15, 2025  
**Maintained By:** AI Troubleshooter v7 Development Team

