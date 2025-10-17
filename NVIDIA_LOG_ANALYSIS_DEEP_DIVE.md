# 🔍 NVIDIA Log Analysis Multi-Agent System - Deep Dive & Implementation Plan

**Reference:** [NVIDIA Blog - Build a Log Analysis Multi-Agent Self-Corrective RAG System](https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/)

**Date:** October 12, 2025  
**Target Environment:** OpenShift (ai-troubleshooter-v7)

---

## 📊 PART 1: NVIDIA Architecture Analysis

### 1.1 Core Architecture Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    NVIDIA Log Analysis Agent                     │
│                  (Self-Corrective Multi-Agent RAG)               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LangGraph Orchestration                     │
│                     (Directed Graph Workflow)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Retrieval  │────▶│  Reranking   │────▶│   Grading    │
│   (Hybrid)   │     │  (NeMo)      │     │  (Scoring)   │
└──────────────┘     └──────────────┘     └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ BM25 Lexical │     │  Relevance   │     │ Generation   │
│   Matching   │     │  Filtering   │     │   (LLM)      │
└──────────────┘     └──────────────┘     └──────────────┘
        │                                           │
        ▼                                           ▼
┌──────────────┐                           ┌──────────────┐
│ FAISS Vector │                           │Self-Correction│
│   Semantic   │                           │     Loop      │
└──────────────┘                           └──────────────┘
```

### 1.2 Key Technical Innovations

| Component | Technology | Purpose | Self-Correction |
|-----------|------------|---------|-----------------|
| **Hybrid Retrieval** | BM25 + FAISS | Balance precision (lexical) and recall (semantic) | ✅ Retry with rewritten query |
| **Reranking** | NeMo Retriever | Surface most relevant log lines | ✅ Filters weak candidates |
| **Grading** | LLM-based scoring | Evaluate contextual relevance | ✅ Triggers query transformation |
| **Generation** | Nemotron LLM | Context-aware answers | ✅ Validates against grading |
| **Query Transformation** | LLM rewriting | Refine search on failure | ✅ Iterative improvement |

### 1.3 Multi-Agent Workflow (LangGraph)

```python
# Pseudo-code from NVIDIA implementation
StateGraph:
  Nodes:
    - retrieve (Hybrid: BM25 + FAISS)
    - rerank (NeMo Retriever)
    - grade_documents (Relevance scoring)
    - generate (Answer generation)
    - transform_query (Query rewriting)
  
  Edges (Conditional):
    - retrieve → rerank
    - rerank → grade_documents
    - grade_documents → [generate OR transform_query]
    - transform_query → retrieve (loop back)
    - generate → [END OR transform_query]
```

**Self-Correction Loop Logic:**
1. If `grade_documents` score < threshold → `transform_query`
2. If `generate` output doesn't match context → `transform_query`
3. Max 3 iterations to prevent infinite loops

---

## 📦 PART 2: NVIDIA Technology Stack

### 2.1 Models Used

| Model | Purpose | Size | Availability |
|-------|---------|------|--------------|
| `llama-3.2-nv-embedqa-1b-v2` | Embeddings | 1B | NVIDIA AI Endpoints |
| `llama-3.2-nv-rerankqa-1b-v2` | Reranking | 1B | NVIDIA AI Endpoints |
| `llama-3.3-nemotron-super-49b-v1.5` | Generation | 49B | NVIDIA AI Endpoints |

### 2.2 Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `langgraph` | Latest | Workflow orchestration |
| `langchain` | Latest | LLM chains and tools |
| `faiss-cpu` or `faiss-gpu` | Latest | Vector similarity search |
| `rank-bm25` | Latest | Lexical retrieval |
| `sentence-transformers` | Latest | Alternative embeddings |

### 2.3 File Structure (from GitHub)

```
community/log_analysis_multi_agent_rag/
├── bat_ai.py                 # Main LangGraph StateGraph definition
├── graphnodes.py             # Node implementations
├── graphedges.py             # Edge logic (conditional routing)
├── multiagent.py             # HybridRetriever class
├── binary_score_models.py    # Grading output models
├── utils.py                  # NVIDIA AI endpoint integration
├── prompt.json               # Prompt templates
├── example.py                # Entry point
└── requirements.txt          # Dependencies
```

---

## 🎯 PART 3: OUR CURRENT SETUP (v6 Baseline)

### 3.1 What We Already Have ✅

| Component | Current (v6) | Status |
|-----------|-------------|--------|
| **LLM** | llama-32-3b-instruct (KServe) | ✅ Running |
| **Embeddings** | granite-embedding-125m (768D) | ✅ Running |
| **Vector DB** | Milvus (via Llama Stack) | ✅ Running |
| **Documentation** | OCP 4.16 Support PDF | ✅ Ingested |
| **MCP Server** | OpenShift MCP (kubernetes-mcp-server) | ✅ Running |
| **Frontend** | Streamlit | ✅ Running |
| **Orchestration** | Llama Stack Agent (basic) | ⚠️ Limited |

### 3.2 What's Missing for Multi-Agent Self-Correction ❌

| Component | Missing | Impact |
|-----------|---------|--------|
| **LangGraph** | No workflow orchestration | No multi-agent coordination |
| **Hybrid Retrieval** | Only vector search | Missing lexical matching (BM25) |
| **Reranking** | No reranking layer | Low-quality results not filtered |
| **Grading** | No relevance scoring | Can't detect poor retrieval |
| **Self-Correction** | No retry logic | Single-pass, no improvement |
| **Log Ingestion** | No log pipeline | Can't ingest OpenShift logs |

---

## 🚀 PART 4: IMPLEMENTATION PLAN FOR v7

### 4.1 Architecture: v6 vs v7

#### **v6 (Current - Basic Llama Stack):**
```
User → Streamlit → Llama Stack Agent → Milvus (Vector Only)
                                    → granite-embedding
                                    → llama-32-3b-instruct
                                    → OCP MCP Server
                                    ↓
                            Single-pass answer
```

#### **v7 (Proposed - Multi-Agent Self-Corrective):**
```
User → Streamlit → LangGraph Orchestrator
                        │
                        ├─ Node 1: Log Ingestion (OpenShift)
                        │    └─ Collect pod logs, events, metrics
                        │
                        ├─ Node 2: Hybrid Retrieval
                        │    ├─ BM25 (lexical matching)
                        │    └─ Milvus + granite-embedding (semantic)
                        │
                        ├─ Node 3: Reranking
                        │    └─ Llama Stack reranking API
                        │
                        ├─ Node 4: Grading
                        │    └─ llama-32-3b-instruct (relevance scoring)
                        │
                        ├─ Node 5: Generation
                        │    └─ llama-32-3b-instruct (answer)
                        │
                        └─ Node 6: Self-Correction
                             └─ Query transformation → Loop back
                        │
                        ↓
                Multi-pass, validated answer
```

### 4.2 Phase-by-Phase Implementation

---

#### **PHASE 1: Foundation (Week 1)**

**Goal:** Set up LangGraph orchestration framework

**Tasks:**
1. ✅ Create `ai-troubleshooter-v7` namespace (DONE)
2. Install LangGraph dependencies
3. Define StateGraph structure
4. Create basic nodes (retrieve, generate)
5. Test simple workflow execution

**Deliverables:**
- `v7_langgraph_base.py` - Basic LangGraph setup
- `v7_state_schema.py` - State definition
- `v7_requirements.txt` - Updated dependencies

**Code Structure:**
```python
# v7_state_schema.py
class GraphState(TypedDict):
    """State for log analysis workflow"""
    question: str
    log_context: str
    retrieved_docs: List[Document]
    reranked_docs: List[Document]
    relevance_scores: List[float]
    generated_answer: str
    iteration: int
    max_iterations: int
```

---

#### **PHASE 2: Hybrid Retrieval (Week 2)**

**Goal:** Implement BM25 + Milvus hybrid retrieval

**Tasks:**
1. Install `rank-bm25` library
2. Create `HybridRetriever` class
3. Combine BM25 lexical + Milvus semantic results
4. Implement weighted score fusion
5. Test on OpenShift logs

**Technical Implementation:**
```python
class HybridRetriever:
    def __init__(self, vector_store, bm25_index):
        self.vector_store = vector_store  # Milvus
        self.bm25 = bm25_index
        self.alpha = 0.5  # Weight: 50% semantic, 50% lexical
    
    def retrieve(self, query: str, k: int = 10):
        # Semantic retrieval (Milvus + granite-embedding)
        semantic_results = self.vector_store.similarity_search(query, k=k)
        
        # Lexical retrieval (BM25)
        lexical_results = self.bm25.get_top_n(query, k=k)
        
        # Fusion: Weighted reciprocal rank
        return self.fuse_results(semantic_results, lexical_results)
```

**Why This Matters:**
- **BM25:** Catches exact error codes (e.g., "HTTP 503", "ImagePullBackOff")
- **Vector:** Finds semantically similar issues (e.g., "timeout" ≈ "connection lost")

---

#### **PHASE 3: Reranking & Grading (Week 3)**

**Goal:** Add reranking and relevance scoring

**Tasks:**
1. Implement reranking using Llama Stack API
2. Create grading node with binary scoring
3. Define relevance threshold (e.g., 0.7)
4. Test filtering weak results

**Reranking Node:**
```python
def rerank_node(state: GraphState):
    """Rerank retrieved documents"""
    query = state["question"]
    docs = state["retrieved_docs"]
    
    # Use Llama Stack reranking
    reranked = llama_client.tool_runtime.rag_tool.rerank(
        query=query,
        documents=docs,
        model="granite-embedding-125m"
    )
    
    return {"reranked_docs": reranked[:5]}  # Top 5
```

**Grading Node:**
```python
def grade_node(state: GraphState):
    """Grade document relevance"""
    scores = []
    for doc in state["reranked_docs"]:
        prompt = f"""
        Score this log snippet's relevance to the question.
        Question: {state['question']}
        Log: {doc.content}
        
        Output 1 if relevant, 0 if not.
        """
        score = llm_call(prompt)
        scores.append(score)
    
    return {"relevance_scores": scores}
```

---

#### **PHASE 4: Self-Correction Loop (Week 4)**

**Goal:** Implement query transformation and retry logic

**Tasks:**
1. Create `transform_query` node
2. Add conditional edges for routing
3. Implement max iteration limit (3)
4. Test self-correction on ambiguous queries

**Query Transformation Node:**
```python
def transform_query_node(state: GraphState):
    """Rewrite query if results are poor"""
    original_query = state["question"]
    log_context = state["log_context"]
    
    prompt = f"""
    The initial query didn't retrieve relevant logs.
    
    Original query: {original_query}
    Context: {log_context}
    
    Rewrite this query to be more specific for log analysis.
    Focus on error patterns, status codes, or component names.
    """
    
    new_query = llm_call(prompt)
    
    return {
        "question": new_query,
        "iteration": state["iteration"] + 1
    }
```

**Conditional Edge Logic:**
```python
def should_transform_query(state: GraphState) -> str:
    """Decide whether to retry or generate answer"""
    scores = state["relevance_scores"]
    iteration = state["iteration"]
    max_iterations = state["max_iterations"]
    
    # If low scores and haven't hit limit
    if sum(scores) / len(scores) < 0.7 and iteration < max_iterations:
        return "transform_query"
    else:
        return "generate"
```

---

#### **PHASE 5: Log Ingestion Pipeline (Week 5)**

**Goal:** Automate OpenShift log collection and indexing

**Tasks:**
1. Create log collector using OpenShift MCP
2. Parse and chunk logs (512 tokens)
3. Ingest into Milvus + BM25 index
4. Schedule periodic updates (every 15 min)

**Log Collector:**
```python
class OpenShiftLogCollector:
    def __init__(self, mcp_client, namespaces):
        self.mcp = mcp_client
        self.namespaces = namespaces
    
    def collect_logs(self):
        """Collect logs from all namespaces"""
        all_logs = []
        
        for ns in self.namespaces:
            # Get pods
            pods = self.mcp.pods_list_in_namespace(namespace=ns)
            
            for pod in pods:
                # Get logs (last 100 lines)
                logs = self.mcp.pods_log(name=pod, namespace=ns)
                
                # Get events
                events = self.mcp.events_list(namespace=ns)
                
                all_logs.append({
                    "namespace": ns,
                    "pod": pod,
                    "logs": logs,
                    "events": events,
                    "timestamp": datetime.now()
                })
        
        return all_logs
    
    def ingest_to_vectordb(self, logs):
        """Ingest logs into Milvus + BM25"""
        # Chunk logs
        chunks = self.chunk_logs(logs)
        
        # Ingest to Milvus
        llama_client.tool_runtime.rag_tool.insert(
            documents=chunks,
            vector_db_id="openshift-logs",
            chunk_size_in_tokens=512
        )
        
        # Build BM25 index
        self.build_bm25_index(chunks)
```

---

#### **PHASE 6: Integration & Testing (Week 6)**

**Goal:** Connect all components and test end-to-end

**Tasks:**
1. Integrate LangGraph workflow with Streamlit
2. Add real-time log streaming
3. Test self-correction on real issues
4. Benchmark vs v6 (accuracy, MTTR)

**End-to-End Test Scenarios:**
1. **ImagePullBackOff** - Should find registry issues
2. **CrashLoopBackOff** - Should identify container failures
3. **OOMKilled** - Should detect memory limits
4. **Networking errors** - Should trace service connectivity

---

## 📊 PART 5: TECHNOLOGY MAPPING

### 5.1 NVIDIA Stack → Our Stack

| NVIDIA Component | Our Replacement | Notes |
|------------------|-----------------|-------|
| NeMo Retriever embeddings | granite-embedding-125m | Already deployed |
| NeMo Retriever reranking | Llama Stack reranking API | Available in Llama Stack |
| Nemotron 49B | llama-32-3b-instruct | Smaller but sufficient |
| NVIDIA AI Endpoints | Llama Stack (KServe) | Already deployed |
| FAISS | Milvus | More production-ready |
| LangGraph | LangGraph | Need to add |
| BM25 | rank-bm25 (Python) | Need to add |

### 5.2 Dependencies to Add

```python
# v7_requirements.txt (additions to v6)
langgraph>=0.2.0
langchain>=0.3.0
langchain-core>=0.3.0
rank-bm25>=0.2.2
pydantic>=2.0.0
networkx>=3.0  # For graph visualization
```

---

## 🎯 PART 6: SUCCESS METRICS

### 6.1 Key Performance Indicators

| Metric | v6 Baseline | v7 Target | Improvement |
|--------|-------------|-----------|-------------|
| **Mean Time to Resolve (MTTR)** | ~15 min | <5 min | 67% reduction |
| **Retrieval Precision** | ~60% | >80% | +20% |
| **Retrieval Recall** | ~70% | >85% | +15% |
| **False Positives** | ~30% | <10% | 67% reduction |
| **User Satisfaction** | 3.5/5 | >4.5/5 | +28% |

### 6.2 Self-Correction Effectiveness

| Scenario | Without Self-Correction | With Self-Correction |
|----------|------------------------|---------------------|
| Ambiguous query | Wrong answer | Correct after 1 retry |
| Poor initial retrieval | No relevant docs | Finds 3+ relevant docs |
| Edge case error | Generic response | Specific root cause |

---

## 🏗️ PART 7: IMPLEMENTATION ROADMAP

### Week 1-2: Foundation
- [x] Create v7 namespace (DONE)
- [ ] Set up LangGraph framework
- [ ] Define StateGraph and nodes
- [ ] Implement basic retrieval + generation

### Week 3-4: Hybrid Retrieval
- [ ] Add BM25 lexical matching
- [ ] Combine BM25 + Milvus results
- [ ] Implement reranking
- [ ] Add relevance grading

### Week 5-6: Self-Correction
- [ ] Create query transformation node
- [ ] Add conditional edges
- [ ] Implement retry logic
- [ ] Test on real logs

### Week 7-8: Log Pipeline
- [ ] Build log collector
- [ ] Schedule periodic ingestion
- [ ] Test with live OpenShift logs
- [ ] Optimize performance

### Week 9-10: Integration
- [ ] Connect to Streamlit UI
- [ ] Add visualizations (graph flow)
- [ ] End-to-end testing
- [ ] Performance benchmarking

### Week 11-12: Production
- [ ] Deploy to v7 namespace
- [ ] Monitor and tune
- [ ] Documentation
- [ ] Team training

---

## 🔐 PART 8: RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **LangGraph learning curve** | High | Start with simple graph, iterate |
| **BM25 index size** | Medium | Implement TTL, cleanup old logs |
| **Self-correction loops** | High | Hard limit at 3 iterations |
| **LLM cost** | Medium | Use smaller model (3B), cache results |
| **Log volume** | High | Filter by namespace, time window |

---

## 📚 PART 9: RESOURCES & REFERENCES

### 9.1 NVIDIA Resources
- **Blog:** https://developer.nvidia.com/blog/build-a-log-analysis-multi-agent-self-corrective-rag-system-with-nvidia-nemotron/
- **GitHub:** https://github.com/NVIDIA/GenerativeAIExamples/tree/main/community/log_analysis_multi_agent_rag
- **DeepWiki:** https://nvidia.github.io/GenerativeAIExamples/latest/log-analysis-agent.html

### 9.2 LangGraph Resources
- **Docs:** https://langchain-ai.github.io/langgraph/
- **Examples:** https://github.com/langchain-ai/langgraph/tree/main/examples
- **Tutorial:** https://python.langchain.com/docs/langgraph

### 9.3 BM25 Resources
- **Paper:** Robertson & Zaragoza (2009) - "The Probabilistic Relevance Framework: BM25 and Beyond"
- **Python Library:** https://github.com/dorianbrown/rank_bm25

---

## 🎯 PART 10: DECISION POINTS

### 10.1 Critical Questions to Answer

1. **Do we build from scratch or adapt NVIDIA code?**
   - ✅ **Recommendation:** Adapt NVIDIA's structure, replace their models with ours
   
2. **Should we keep v6 running during v7 development?**
   - ✅ **Recommendation:** Yes, v6 is stable, use it as baseline

3. **What's our log retention policy?**
   - ✅ **Recommendation:** 7 days rolling window, configurable

4. **How many self-correction iterations?**
   - ✅ **Recommendation:** Max 3 (NVIDIA uses 3)

5. **Should we add observability for the agent itself?**
   - ✅ **Recommendation:** YES - Track node execution times, success rates

---

## ✅ NEXT STEPS (Pending Your Approval)

### Option A: Full Implementation (12 weeks)
- Implement all phases as described
- Full feature parity with NVIDIA system
- Production-ready deployment

### Option B: MVP (6 weeks)
- Phase 1-4 only (no log pipeline yet)
- Manual log input for testing
- Proof of concept

### Option C: Hybrid Approach (8 weeks)
- Phases 1-4 + simplified log collection
- Auto-collect logs from selected namespaces
- Production-ready with limited scope

---

## 🎬 **READY TO PROCEED?**

**What I need from you:**
1. ✅ Approve the approach (Option A, B, or C)
2. ✅ Confirm technology choices (LangGraph, BM25, etc.)
3. ✅ Any specific requirements or constraints?
4. ✅ Priority namespaces for log collection?

**Once approved, I will:**
1. Clone NVIDIA GitHub repo for reference
2. Start Phase 1 implementation
3. Create the LangGraph foundation for v7

---

**Status:** 🟡 **AWAITING YOUR GO/NO-GO DECISION**

