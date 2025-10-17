# 🏗️ AI Troubleshooter v7 - Architecture Diagrams

Comprehensive visual architecture documentation

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│                     AI Troubleshooter v7 Architecture                        │
│                   Multi-Agent Self-Corrective RAG System                     │
│                                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

                                    USER
                                     │
                                     │ HTTPS (TLS Edge)
                                     ▼
                    ┌─────────────────────────────────────┐
                    │    OpenShift Route                  │
                    │    ai-troubleshooter-v7            │
                    │    (TLS Termination)               │
                    └─────────────────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────┐
                    │    Service (ClusterIP)             │
                    │    Port: 8501                       │
                    └─────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Pod: ai-troubleshooter-v7-xxxxxxxxx-xxxxx                                 │
│  ServiceAccount: ai-troubleshooter-v7-sa (ClusterRole: reader)             │
│  Image: registry.access.redhat.com/ubi9/python-311:latest                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Streamlit Frontend (Port 8501)                   │  │
│  │  • User Interface                                                     │  │
│  │  • 6 Result Tabs                                                      │  │
│  │  • Progress Tracking                                                  │  │
│  │  • Configuration Controls                                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │            Kubernetes Data Collector (oc commands)                   │  │
│  │  • get namespaces                                                     │  │
│  │  • get pods -n {namespace}                                           │  │
│  │  • logs {pod} -n {namespace}                                         │  │
│  │  • get events -n {namespace}                                         │  │
│  │  • describe pod {pod} -n {namespace}                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph Multi-Agent Workflow                    │  │
│  │                                                                       │  │
│  │    ┌──────────┐      ┌──────────┐      ┌──────────┐               │  │
│  │    │ RETRIEVE │─────▶│  RERANK  │─────▶│  GRADE   │               │  │
│  │    └──────────┘      └──────────┘      └──────────┘               │  │
│  │         ▲                                     │                      │  │
│  │         │                                     ▼                      │  │
│  │         │                              ┌──────────┐                 │  │
│  │         │                              │ GENERATE │                 │  │
│  │         │                              └──────────┘                 │  │
│  │         │                                     │                      │  │
│  │         │                                     ▼                      │  │
│  │         │                              ┌──────────┐                 │  │
│  │         └──────────────────────────────│TRANSFORM │                 │  │
│  │                                        │  QUERY   │                 │  │
│  │                                        └──────────┘                 │  │
│  │                                                                       │  │
│  │    Self-Correction Loop (Max 3 Iterations)                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Hybrid Retriever Engine                           │  │
│  │                                                                       │  │
│  │    ┌─────────────────────┐         ┌──────────────────────┐        │  │
│  │    │   BM25 (Lexical)    │         │  Milvus (Semantic)   │        │  │
│  │    │                     │         │                      │        │  │
│  │    │ • Keyword matching  │         │ • Vector similarity  │        │  │
│  │    │ • Error codes       │    +    │ • Embeddings search  │        │  │
│  │    │ • Exact strings     │         │ • Conceptual match   │        │  │
│  │    │ • In-memory index   │         │ • Optional (via API) │        │  │
│  │    └─────────────────────┘         └──────────────────────┘        │  │
│  │              │                               │                       │  │
│  │              └───────────┬───────────────────┘                       │  │
│  │                          ▼                                           │  │
│  │              Reciprocal Rank Fusion (RRF)                           │  │
│  │              score = Σ[1 / (k + rank)]                              │  │
│  │                          │                                           │  │
│  │                          ▼                                           │  │
│  │                  Top 10 Relevant Logs                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Llama Stack Client                                │  │
│  │  • Chat Completion API                                                │  │
│  │  • RAG Tool (Vector DB Query)                                        │  │
│  │  • Model: llama-32-3b-instruct                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
└─────────────────────────────────┼────────────────────────────────────────────┘
                                  │
                                  │ HTTP (Internal)
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Namespace: model                                                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │    Service: llamastack-custom-distribution-service                   │  │
│  │    Port: 8321                                                         │  │
│  │    Pod: llamastack-custom-distribution-xxx                           │  │
│  │                                                                       │  │
│  │    APIs:                                                              │  │
│  │    • /v1/inference/chat-completion                                   │  │
│  │    • /v1/tool-runtime/rag-tool/query                                 │  │
│  │    • /v1/models                                                       │  │
│  │    • /v1/health                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 │                                            │
│                  ┌──────────────┼──────────────┐                            │
│                  │              │              │                            │
│                  ▼              ▼              ▼                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐           │
│  │  LLM Model      │  │  Embedding      │  │  Vector DB      │           │
│  │  Llama 3.2 3B   │  │  Granite 125M   │  │  Milvus         │           │
│  │  KServe/VLLM    │  │  768 dimensions │  │  (Optional)     │           │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │    Service: ocp-mcp-server (Model Context Protocol)                 │  │
│  │    Port: 8000                                                         │  │
│  │    Provides: Cluster introspection tools (optional)                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Agent Workflow (LangGraph)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LangGraph State Machine                              │
│                       (Multi-Agent Orchestration)                            │
└─────────────────────────────────────────────────────────────────────────────┘

                                   START
                                     │
                                     ▼
                    ╔════════════════════════════════╗
                    ║   GraphState (Shared State)    ║
                    ║                                ║
                    ║ • question: str                ║
                    ║ • log_context: str             ║
                    ║ • pod_events: str              ║
                    ║ • retrieved_docs: List         ║
                    ║ • reranked_docs: List          ║
                    ║ • relevance_scores: List       ║
                    ║ • generation: str              ║
                    ║ • iteration: int               ║
                    ║ • transformation_history: List ║
                    ╚════════════════════════════════╝
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │  NODE 1: RETRIEVE                                      │
        │  Agent: Hybrid Retriever                               │
        │                                                         │
        │  Input:  question, log_context, pod_events             │
        │  Process:                                               │
        │    1. Split logs into lines (documents)                │
        │    2. Build BM25 index (tokenize, index)              │
        │    3. BM25 search (keyword matching)                   │
        │    4. Milvus search (semantic, optional)              │
        │    5. RRF fusion (combine rankings)                    │
        │  Output: retrieved_docs (Top 10)                       │
        └────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │  NODE 2: RERANK                                        │
        │  Agent: Score-Based Reranker                           │
        │                                                         │
        │  Input:  retrieved_docs                                │
        │  Process:                                               │
        │    1. Sort by relevance score (descending)            │
        │    2. Take top 5 documents                             │
        │  Output: reranked_docs (Top 5)                         │
        └────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │  NODE 3: GRADE DOCUMENTS                               │
        │  Agent: LLM-Based Document Grader                      │
        │                                                         │
        │  Input:  reranked_docs, question                       │
        │  Process:                                               │
        │    For each document:                                  │
        │      1. Create grading prompt                          │
        │      2. LLM scores relevance (0.0-1.0)                │
        │      3. Keep if score ≥ 0.6                           │
        │  Output: relevance_scores, filtered reranked_docs      │
        └────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        ┌────────────────────────────────────────────────────────┐
        │  DECISION: Should we generate or transform query?      │
        │  Function: decide_to_generate()                        │
        │                                                         │
        │  Logic:                                                 │
        │    IF len(reranked_docs) > 0:                         │
        │        → GENERATE                                      │
        │    ELIF iteration < max_iterations:                    │
        │        → TRANSFORM QUERY (retry)                      │
        │    ELSE:                                               │
        │        → GENERATE (give up, do best effort)           │
        └────────────────────────────────────────────────────────┘
                   │                                  │
                   │ (has docs)                       │ (no docs)
                   ▼                                  ▼
    ┌──────────────────────┐           ┌──────────────────────────────┐
    │  NODE 4: GENERATE    │           │  NODE 5: TRANSFORM QUERY     │
    │  Agent: LLM Analyzer │           │  Agent: Query Rewriter       │
    │                      │           │                              │
    │  Input: question,    │           │  Input: question, feedback,  │
    │         reranked_docs│           │         original_question    │
    │         pod_status   │           │  Process:                    │
    │  Process:            │           │    1. Analyze why failed     │
    │    1. Build context  │           │    2. LLM rewrites query     │
    │    2. Create prompt  │           │    3. Make more specific     │
    │    3. LLM generates  │           │    4. Add keywords           │
    │       troubleshooting│           │  Output: new question,       │
    │       analysis       │           │          iteration++         │
    │  Output: generation  │           └──────────────────────────────┘
    └──────────────────────┘                          │
                   │                                  │
                   │                                  │ (loop back)
                   │                                  │
                   ▼                                  ▼
    ┌──────────────────────────────────────────────────────────┐
    │  DECISION: Is the answer good enough?                    │
    │  Function: grade_generation_vs_documents_and_question()  │
    │                                                           │
    │  Logic:                                                   │
    │    IF len(generation) > 100 AND has_docs:                │
    │        → USEFUL (success, end)                           │
    │    ELIF len(generation) < 50 AND iteration < max:        │
    │        → NOT USEFUL (retry)                              │
    │    ELIF "no relevant" in generation AND iteration < max: │
    │        → NOT USEFUL (retry)                              │
    │    ELSE:                                                  │
    │        → USEFUL (accept)                                 │
    └──────────────────────────────────────────────────────────┘
                   │                                  │
                   │ (useful)                         │ (not useful)
                   ▼                                  │
                  END ◄──────────────────────────────┘
                   │
                   ▼
        ┌──────────────────────────────────────────┐
        │  FINAL STATE                             │
        │  • generation (answer)                   │
        │  • reranked_docs (evidence)              │
        │  • iteration (# of retries)              │
        │  • transformation_history (query changes)│
        └──────────────────────────────────────────┘
```

---

## 3. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Data Flow (End-to-End)                            │
└─────────────────────────────────────────────────────────────────────────────┘

USER ACTION: Click "🚀 Start Multi-Agent Analysis"
    │
    ▼
[Streamlit: Collect Input]
    ├─ selected_namespace: "test-problematic-pods"
    ├─ selected_pod: "crash-loop-app-xxx"
    ├─ include_logs: True
    ├─ include_events: True
    └─ max_iterations: 3
    │
    ▼
[KubernetesDataCollector: Collect Data]
    ├─ oc get pod {pod} -n {ns} -o json → pod_info
    ├─ oc logs {pod} -n {ns} --tail=100 → logs (12,345 chars)
    └─ oc get events -n {ns} → events (28 events)
    │
    ▼
[Build Question]
    ├─ IF pod_status != "Running":
    │     question = "Why is pod in {status} state?"
    └─ ELSE:
          question = "Analyze pod for any issues or errors"
    │
    ▼
[Initialize GraphState]
    ├─ question: "Analyze pod crash-loop-app for errors"
    ├─ namespace: "test-problematic-pods"
    ├─ pod_name: "crash-loop-app-xxx"
    ├─ log_context: "2025-10-12 14:23:45 FATAL: out of memory\n..."
    ├─ pod_events: "Back-off restarting failed container\n..."
    ├─ pod_status: {phase: "Running", restartCount: 8, ...}
    ├─ retrieved_docs: []
    ├─ reranked_docs: []
    ├─ generation: ""
    ├─ iteration: 0
    └─ max_iterations: 3
    │
    ▼
════════════════════════════════════════════════════════════════════════════════
                            LANGGRAPH EXECUTION
════════════════════════════════════════════════════════════════════════════════
    │
    ▼
[NODE: RETRIEVE]
    │
    ├─ Split log_context into lines
    │     Input: "2025-10-12 14:23:45 FATAL: out of memory\n..."
    │     Output: ["2025-10-12 14:23:45 FATAL: out of memory", ...]
    │     Count: 103 log lines
    │
    ├─ Build BM25 Index
    │     ├─ Tokenize each line: ["2025", "10", "12", "fatal", "out", "of", "memory"]
    │     ├─ Build BM25Okapi index (103 documents)
    │     └─ Index size: ~500KB in memory
    │
    ├─ BM25 Search
    │     Query: "analyze pod crash-loop-app for errors"
    │     Tokens: ["analyze", "pod", "crash", "loop", "app", "errors"]
    │     ├─ Compute BM25 scores for each document
    │     └─ Top 10: [doc_45 (score=12.3), doc_67 (score=11.8), ...]
    │
    ├─ Milvus Search (Optional)
    │     Query: "analyze pod crash-loop-app for errors"
    │     ├─ Embed query → [0.123, -0.456, ...] (768 dimensions)
    │     ├─ Milvus similarity search
    │     └─ Result: Error (Vector DB not available) → Fallback to BM25 only
    │
    ├─ RRF Fusion
    │     BM25 results: 8 documents
    │     Vector results: 0 documents
    │     ├─ Compute RRF scores: score = Σ[1 / (60 + rank)]
    │     └─ Combined top 10: [doc_45, doc_67, doc_23, ...]
    │
    └─ Output: retrieved_docs = [
          {content: "2025-10-12 14:23:45 FATAL: out of memory", score: 12.3, method: "bm25"},
          {content: "2025-10-12 14:23:47 Container exited with code 137", score: 11.8, method: "bm25"},
          ...
       ] (10 documents)
    │
    ▼
[NODE: RERANK]
    │
    ├─ Input: 10 documents
    ├─ Sort by score (descending)
    └─ Output: reranked_docs = Top 5 documents
    │
    ▼
[NODE: GRADE]
    │
    ├─ For each of 5 documents:
    │     ├─ Build prompt: "Grade relevance: Question: ... Log: ..."
    │     ├─ LLM call → response: "0.92"
    │     ├─ Parse score: 0.92
    │     └─ Keep if ≥ 0.6
    │
    ├─ Results:
    │     ├─ Doc 1: 0.92 ✅
    │     ├─ Doc 2: 0.88 ✅
    │     ├─ Doc 3: 0.73 ✅
    │     ├─ Doc 4: 0.65 ✅
    │     └─ Doc 5: 0.42 ❌
    │
    └─ Output: reranked_docs = 4 documents, relevance_scores = [0.92, 0.88, 0.73, 0.65]
    │
    ▼
[DECISION: GENERATE]
    ├─ Check: len(reranked_docs) = 4 > 0? YES
    └─ Route: GENERATE
    │
    ▼
[NODE: GENERATE]
    │
    ├─ Build context from top 4 logs:
    │     "Log 1: 2025-10-12 14:23:45 FATAL: out of memory
    │      Log 2: 2025-10-12 14:23:47 Container exited with code 137
    │      Log 3: Back-off restarting failed container
    │      Log 4: OOMKilled"
    │
    ├─ Build prompt:
    │     "You are a senior OpenShift SRE...
    │      Question: Analyze pod crash-loop-app for errors
    │      Relevant Logs: [context]
    │      Pod Context: {phase: Running, restartCount: 8, ...}
    │      Provide: ISSUE, REFERENCES, ACTIONS, FIX"
    │
    ├─ LLM call (Llama 3.2 3B)
    │     ├─ Model: llama-32-3b-instruct
    │     ├─ Max tokens: 500
    │     └─ Temperature: 0 (greedy)
    │
    └─ Output: generation = "
          🚨 ISSUE: Pod experiencing OOMKilled (Out of Memory)
          
          📚 REFERENCES:
            • Log Line 45: 'FATAL: out of memory'
            • Log Line 67: 'Exit code: 137 (OOMKilled)'
            • Event: 'Back-off restarting failed container'
          
          ⚡ ACTIONS:
            1. oc describe pod crash-loop-app-xxx -n test-problematic-pods
            2. oc logs crash-loop-app-xxx -n test-problematic-pods --previous
            3. oc set resources deployment crash-loop-app --limits=memory=2Gi
          
          🔧 FIX:
            Container exceeding 512Mi memory limit. Increase to 1Gi or optimize app.
       " (243 words)
    │
    ▼
[DECISION: IS ANSWER GOOD?]
    ├─ Check: len(generation) = 243 > 100? YES
    ├─ Check: has docs = 4 > 0? YES
    ├─ Check: "no relevant" in generation? NO
    └─ Route: USEFUL (END)
    │
    ▼
════════════════════════════════════════════════════════════════════════════════
                         WORKFLOW COMPLETE
════════════════════════════════════════════════════════════════════════════════
    │
    ▼
[FINAL STATE]
    ├─ generation: "🚨 ISSUE: Pod experiencing OOMKilled..."
    ├─ reranked_docs: [4 relevant logs]
    ├─ relevance_scores: [0.92, 0.88, 0.73, 0.65]
    ├─ iteration: 1 (only needed 1 iteration!)
    └─ transformation_history: [] (no transformations needed)
    │
    ▼
[Return to Streamlit]
    ├─ success: True
    ├─ answer: "🚨 ISSUE: ..."
    ├─ relevant_docs: [4 logs]
    ├─ iterations: 1
    └─ metadata: {retrieval_time: 1.2s, llm_time: 2.1s, ...}
    │
    ▼
[Display in UI]
    ├─ Tab 1: Multi-Agent Analysis → Show "🚨 ISSUE: ..."
    ├─ Tab 2: Evidence → Show 4 relevant logs with scores
    ├─ Tab 3: Workflow → Show node execution trace
    ├─ Tab 4: Pod Details → Show oc describe output
    ├─ Tab 5: Metrics → Show 10 retrieved, 4 relevant, 1 iteration
    └─ Tab 6: Storage → Show PVC status
    │
    ▼
USER SEES RESULT (Total time: ~5 seconds)
```

---

## 4. RBAC & Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RBAC & Security Architecture                          │
└─────────────────────────────────────────────────────────────────────────────┘

                          ┌─────────────────────┐
                          │   ServiceAccount    │
                          │ ai-troubleshooter-  │
                          │      v7-sa          │
                          │                     │
                          │ Namespace:          │
                          │ ai-troubleshooter-v7│
                          └─────────────────────┘
                                    │
                                    │ bound to
                                    ▼
                          ┌─────────────────────┐
                          │  ClusterRoleBinding │
                          │ ai-troubleshooter-  │
                          │   v7-binding        │
                          └─────────────────────┘
                                    │
                                    │ references
                                    ▼
                          ┌─────────────────────┐
                          │    ClusterRole      │
                          │ ai-troubleshooter-  │
                          │    v7-reader        │
                          │                     │
                          │  PERMISSIONS        │
                          │  (Read-Only)        │
                          └─────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │  Core API     │ │  Apps API     │ │  Route API    │
        │  Group: ""    │ │  Group: apps  │ │  Group:       │
        │               │ │               │ │  route.       │
        │  Resources:   │ │  Resources:   │ │  openshift.io │
        │  • namespaces │ │  • deployments│ │               │
        │  • pods       │ │  • replicasets│ │  Resources:   │
        │  • pods/log   │ │  • statefulset│ │  • routes     │
        │  • events     │ │               │ │               │
        │  • pvcs       │ │  Verbs:       │ │  Verbs:       │
        │  • services   │ │  • get        │ │  • get        │
        │               │ │  • list       │ │  • list       │
        │  Verbs:       │ └───────────────┘ └───────────────┘
        │  • get        │
        │  • list       │
        │  • watch      │
        └───────────────┘

What CAN the ServiceAccount do?
✅ List all namespaces across cluster
✅ List all pods in any namespace
✅ Read pod logs from any pod
✅ List events in any namespace
✅ Get pod details (oc describe)
✅ List PVCs, deployments, services
✅ List OpenShift routes

What CANNOT the ServiceAccount do?
❌ Create/delete/update any resources
❌ Execute commands inside pods (except via oc exec which is read-only)
❌ Read secrets
❌ Modify RBAC roles/bindings
❌ Access node resources
❌ Create/delete namespaces
❌ Scale deployments
❌ Restart pods (except by deleting them, which it can't do)

Network Security:
┌─────────────────────────────────────────────────────────────┐
│  Inbound Traffic:                                            │
│  ├─ User Browser → Route (HTTPS, TLS edge termination)      │
│  └─ Only port 8501 exposed                                  │
│                                                               │
│  Outbound Traffic:                                           │
│  ├─ Pod → Kubernetes API Server (authenticated via SA token)│
│  ├─ Pod → Llama Stack (HTTP, internal ClusterIP)           │
│  └─ No external internet access                             │
│                                                               │
│  ServiceAccount Token:                                       │
│  ├─ Auto-mounted at /var/run/secrets/kubernetes.io/...     │
│  ├─ Used by oc client for authentication                    │
│  └─ Scoped to ClusterRole permissions                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Deployment Architecture                              │
└─────────────────────────────────────────────────────────────────────────────┘

Namespace: ai-troubleshooter-v7
│
├─ ConfigMap: ai-troubleshooter-v7-code
│  ├─ app.py (v7_streamlit_app.py)
│  ├─ state_schema.py (v7_state_schema.py)
│  ├─ hybrid_retriever.py (v7_hybrid_retriever.py)
│  ├─ graph_nodes.py (v7_graph_nodes.py)
│  ├─ graph_edges.py (v7_graph_edges.py)
│  ├─ main_graph.py (v7_main_graph.py)
│  └─ log_collector.py (v7_log_collector.py)
│
├─ ServiceAccount: ai-troubleshooter-v7-sa
│  └─ Bound to ClusterRole via ClusterRoleBinding
│
├─ Deployment: ai-troubleshooter-v7
│  │
│  ├─ Replicas: 1
│  ├─ Strategy: RollingUpdate
│  ├─ Selector: app=ai-troubleshooter-v7
│  │
│  └─ Pod Template:
│     │
│     ├─ Labels:
│     │  ├─ app: ai-troubleshooter-v7
│     │  ├─ version: v7
│     │  └─ component: multi-agent-rag
│     │
│     ├─ ServiceAccount: ai-troubleshooter-v7-sa
│     │
│     └─ Container: streamlit-app
│        │
│        ├─ Image: registry.access.redhat.com/ubi9/python-311:latest
│        │
│        ├─ Command: /bin/bash
│        │
│        ├─ Args:
│        │  └─ -c |
│        │     1. Install oc client → ~/bin/oc
│        │     2. pip install dependencies (fire, langgraph, llama-stack-client, ...)
│        │     3. Copy code from /app-config/*.py → /tmp/
│        │     4. streamlit run /tmp/app.py --port 8501
│        │
│        ├─ Environment Variables:
│        │  ├─ LLAMA_STACK_URL: http://llamastack-custom-distribution-service.model...
│        │  ├─ LLAMA_STACK_MODEL: llama-32-3b-instruct
│        │  ├─ EMBEDDING_MODEL: granite-embedding-125m
│        │  ├─ EMBEDDING_DIMENSION: 768
│        │  ├─ VECTOR_DB_ID: openshift-logs-v7
│        │  └─ MAX_ITERATIONS: 3
│        │
│        ├─ Ports:
│        │  └─ containerPort: 8501 (TCP)
│        │
│        ├─ Resources:
│        │  ├─ Requests: CPU 250m, Memory 512Mi
│        │  └─ Limits: CPU 1, Memory 2Gi
│        │
│        ├─ Liveness Probe:
│        │  ├─ httpGet: path=/, port=8501
│        │  ├─ initialDelaySeconds: 120
│        │  └─ periodSeconds: 30
│        │
│        ├─ Readiness Probe:
│        │  ├─ httpGet: path=/, port=8501
│        │  ├─ initialDelaySeconds: 60
│        │  └─ periodSeconds: 10
│        │
│        └─ Volume Mounts:
│           └─ /app-config → ConfigMap (ai-troubleshooter-v7-code)
│
├─ Service: ai-troubleshooter-v7-service
│  ├─ Type: ClusterIP
│  ├─ Selector: app=ai-troubleshooter-v7
│  └─ Ports:
│     └─ name: http, port: 8501, targetPort: 8501
│
└─ Route: ai-troubleshooter-v7
   ├─ Host: ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123...
   ├─ To: Service/ai-troubleshooter-v7-service
   ├─ Port: targetPort: http (8501)
   ├─ TLS:
   │  ├─ termination: edge
   │  └─ insecureEdgeTerminationPolicy: Redirect
   └─ Wildcard Policy: None

Startup Sequence:
1. [0s]   Pod scheduled, pull image (registry.access.redhat.com/ubi9/python-311)
2. [10s]  Image pulled, container starts, bash script begins
3. [15s]  Download oc client (~70MB)
4. [25s]  Install pip dependencies (~120s)
5. [145s] Copy code from ConfigMap to /tmp/
6. [150s] Start Streamlit on port 8501
7. [155s] Readiness probe succeeds (HTTP 200 on /)
8. [160s] Service routes traffic to pod
9. [165s] Route becomes accessible (HTTPS)

Total startup time: ~2.5-3 minutes
```

---

---

## 6. Future Enterprise Architecture (ServiceNow Integration)

**Note**: This is the **FUTURE** enterprise extension. Current v7 uses BM25-only (no vector DB required).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│           FUTURE: Enterprise RAG with ServiceNow Integration                │
│                      (2-Source Hybrid Knowledge System)                      │
└─────────────────────────────────────────────────────────────────────────────┘

KNOWLEDGE SOURCES (2):
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│     ┌──────────────────────────┐              ┌──────────────────────────┐  │
│     │      ServiceNow KB       │              │      Live Pods           │  │
│     │   (Customer Knowledge)   │              │   (OpenShift Cluster)    │  │
│     │                          │              │                          │  │
│     │  • Past Incidents        │              │  • Pod Logs (100 lines)  │  │
│     │  • INC001234             │              │  • Kubernetes Events     │  │
│     │  • Tested Resolutions    │              │  • Pod Status            │  │
│     │  • Root Cause Analysis   │              │  • Real-time Data        │  │
│     │  • Company-specific      │              │  • Ephemeral             │  │
│     │  • Proven fixes ✅       │              │  • Current state ✅      │  │
│     └────────────┬─────────────┘              └────────────┬─────────────┘  │
│                  │                                          │                │
│                  │ (Webhook on ticket close)                │ (oc commands)  │
│                  │                                          │                │
│                  ▼                                          ▼                │
│     ┌──────────────────────────┐              ┌──────────────────────────┐  │
│     │   Milvus Vector DB       │              │     BM25 Index           │  │
│     │   (Persistent)           │              │     (In-Memory)          │  │
│     │                          │              │                          │  │
│     │  Collection: customer-kb │              │  Built per analysis      │  │
│     │  • Semantic search       │              │  • Keyword matching      │  │
│     │  • Embedding: Granite    │              │  • Lexical search        │  │
│     │  • 768 dimensions        │              │  • ~100-200 documents    │  │
│     │  • Auto-updated          │              │  • Tokenized logs        │  │
│     └────────────┬─────────────┘              └────────────┬─────────────┘  │
│                  │                                          │                │
└──────────────────┼──────────────────────────────────────────┼────────────────┘
                   │                                          │
                   └──────────────────┬───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│               AI TROUBLESHOOTER v7 (2-Source Hybrid RAG)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                 HYBRID RETRIEVAL (2 Sources)                          │  │
│  │                                                                        │  │
│  │  User Query: "Pod crash-loop-app in CrashLoopBackOff"                │  │
│  │                                                                        │  │
│  │     ┌─────────────────────────┐        ┌─────────────────────────┐   │  │
│  │     │   ServiceNow Search     │        │   Live Logs Search      │   │  │
│  │     │   (Milvus Vector)       │        │   (BM25 Keyword)        │   │  │
│  │     │                         │        │                         │   │  │
│  │     │  Query: Semantic        │        │  Query: Keywords        │   │  │
│  │     │  "Similar past issues"  │        │  "OOM, crash, error"    │   │  │
│  │     │                         │        │                         │   │  │
│  │     │  Embedding → 768D       │        │  Tokenize → BM25        │   │  │
│  │     │  Search Milvus          │        │  Search index           │   │  │
│  │     │                         │        │                         │   │  │
│  │     │  Results:               │        │  Results:               │   │  │
│  │     │  • INC001234 ✅         │        │  • "FATAL: OOM"         │   │  │
│  │     │    (Score: 0.92)        │        │    (Score: 12.3)        │   │  │
│  │     │  • INC005678            │        │  • "Exit code 137"      │   │  │
│  │     │    (Score: 0.81)        │        │    (Score: 11.8)        │   │  │
│  │     │  • ... (Top 10)         │        │  • ... (Top 10)         │   │  │
│  │     └───────────┬─────────────┘        └───────────┬─────────────┘   │  │
│  │                 │                                  │                  │  │
│  │                 └──────────────┬───────────────────┘                  │  │
│  │                                │                                      │  │
│  │                                ▼                                      │  │
│  │                   ┌─────────────────────────┐                        │  │
│  │                   │   RRF FUSION            │                        │  │
│  │                   │   (2-way merge)         │                        │  │
│  │                   │                         │                        │  │
│  │                   │  Formula:               │                        │  │
│  │                   │  score = Σ[1/(k+rank)]  │                        │  │
│  │                   │                         │                        │  │
│  │                   │  Combines:              │                        │  │
│  │                   │  • ServiceNow rankings  │                        │  │
│  │                   │  • Live log rankings    │                        │  │
│  │                   │                         │                        │  │
│  │                   │  Boosts documents       │                        │  │
│  │                   │  that rank HIGH in      │                        │  │
│  │                   │  BOTH systems! 🏆       │                        │  │
│  │                   └───────────┬─────────────┘                        │  │
│  │                               │                                      │  │
│  │                               ▼                                      │  │
│  │                   ┌─────────────────────────┐                        │  │
│  │                   │   SMART DECISION        │                        │  │
│  │                   │                         │                        │  │
│  │                   │  IF ServiceNow match    │                        │  │
│  │                   │  with score > 0.8:      │                        │  │
│  │                   │  ────────────────────   │                        │  │
│  │                   │  ✅ Use proven solution │                        │  │
│  │                   │     from INC001234      │                        │  │
│  │                   │                         │                        │  │
│  │                   │  ELSE:                  │                        │  │
│  │                   │  ────────────────────   │                        │  │
│  │                   │  🤖 Generate new        │                        │  │
│  │                   │     solution using      │                        │  │
│  │                   │     LLM + live logs     │                        │  │
│  │                   └───────────┬─────────────┘                        │  │
│  │                               │                                      │  │
│  │                               ▼                                      │  │
│  │                   ┌─────────────────────────┐                        │  │
│  │                   │   FINAL ANSWER          │                        │  │
│  │                   │   (Tagged by source)    │                        │  │
│  │                   │                         │                        │  │
│  │                   │  Option A:              │                        │  │
│  │                   │  🎫 [ServiceNow]        │                        │  │
│  │                   │  "Known issue INC001234 │                        │  │
│  │                   │   Tested solution:      │                        │  │
│  │                   │   oc set resources...   │                        │  │
│  │                   │   Root cause: Memory    │                        │  │
│  │                   │   leak in v2.3"         │                        │  │
│  │                   │                         │                        │  │
│  │                   │  Option B:              │                        │  │
│  │                   │  🤖 [AI Generated]      │                        │  │
│  │                   │  "New issue detected    │                        │  │
│  │                   │   Analysis: ...         │                        │  │
│  │                   │   Recommendation: ..."  │                        │  │
│  │                   │                         │                        │  │
│  │                   │  + Confidence score     │                        │  │
│  │                   │  + Source references    │                        │  │
│  │                   └───────────┬─────────────┘                        │  │
│  └───────────────────────────────┼───────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │   FEEDBACK LOOP             │
                    │                             │
                    │  IF answer = [AI Generated]:│
                    │  ─────────────────────────  │
                    │  • Save to ServiceNow       │
                    │  • Create ticket with       │
                    │    resolution               │
                    │  • Embed & index            │
                    │  • Available for next time  │
                    │                             │
                    │  System learns! 🔄          │
                    └─────────────────────────────┘
```

---

### Key Benefits of ServiceNow Integration

**1. Customer-Specific Knowledge**
- Uses YOUR company's proven solutions
- No generic documentation
- Real resolutions that worked before

**2. Prioritizes Proven Solutions**
```
Decision Logic:
├─ IF ServiceNow has high-confidence match (>0.8)
│  └─ Use tested solution ✅
├─ ELSE
│  └─ Generate new solution with LLM 🤖
└─ Always tag answer with source
```

**3. Learning System**
```
Continuous Improvement:
Issue → Analysis → Resolution → ServiceNow → Future reuse
                                    ↑                 │
                                    └─────────────────┘
                                      Feedback Loop
```

**4. Multi-Source Intelligence**
- **ServiceNow**: What worked before?
- **Live Logs**: What's happening now?
- **RRF Fusion**: Best of both worlds

**5. Real-Time + Historical**
- Historical: ServiceNow KB (persistent knowledge)
- Real-Time: Live pod logs (current state)
- Combined: Comprehensive analysis

---

### Example Flow with ServiceNow

**Scenario:** Pod OOMKilled in production

**Step 1: Query ServiceNow**
```
Search Milvus: "pod oomkilled crashloopbackoff"
Result: INC001234 (Confidence: 0.92)
  - Issue: "Pod OOMKilled due to memory leak"
  - Resolution: "Increase memory to 1Gi"
  - Root Cause: "Memory leak in v2.3"
  - Tested: ✅ 2025-09-15
```

**Step 2: Query Live Logs**
```
Search BM25: "oom killed error"
Result: 
  - "FATAL: out of memory" (Score: 12.3)
  - "Exit code 137 OOMKilled" (Score: 11.8)
  - Confirms same issue!
```

**Step 3: RRF Fusion**
```
Combined Evidence:
  ✅ ServiceNow: High confidence (0.92)
  ✅ Live Logs: Confirms same pattern (OOM)
  → Decision: Use ServiceNow solution
```

**Step 4: Answer**
```
🎫 KNOWN ISSUE (ServiceNow INC001234)

Your team solved this on 2025-09-15

Root Cause: Memory leak in application v2.3

Tested Solution:
oc set resources deployment crash-loop-app \
  --limits=memory=1Gi --requests=memory=512Mi

Resolution confirmed working by:
  - SRE Team (John Doe)
  - Incident closed: 2025-09-15
  
Confidence: 92%
Source: ServiceNow INC001234
```

---

### Implementation Considerations

**1. ServiceNow Webhook Setup**
```
Trigger: Ticket status → Closed with resolution
Action: POST to /api/ingest-resolution
Payload:
  - Incident ID
  - Title & Description
  - Resolution steps
  - Root cause analysis
  - Timestamps
```

**2. Vector DB Setup**
```
Register with Llama Stack:
  vector_db_id: "customer-kb"
  embedding_model: "granite-embedding-125m"
  dimension: 768
  provider: "milvus"

Ingest ServiceNow data:
  - Embed resolution text
  - Store metadata (INC ID, date, SRE)
  - Index for fast search
```

**3. Query Strategy**
```
Parallel queries (async):
  ├─ ServiceNow: Semantic search
  └─ Live Logs: BM25 keyword search

Wait for both → RRF fusion → Decision
```

**4. Decision Threshold**
```
IF servicenow_score > 0.8 AND logs_confirm_issue:
    return servicenow_solution
ELIF servicenow_score > 0.6:
    return hybrid_answer (ServiceNow + Generated)
ELSE:
    return generated_solution
```

---

### Comparison: Current v7 vs Future Enterprise

| Feature | Current v7 | Future Enterprise |
|---------|------------|-------------------|
| **Knowledge Sources** | Live logs only | ServiceNow + Live logs |
| **Vector DB** | Optional (not used) | Required for ServiceNow |
| **Retrieval** | BM25 only | Hybrid (BM25 + Milvus) |
| **RRF Fusion** | N/A (single source) | 2-way fusion |
| **Knowledge Type** | Real-time only | Historical + Real-time |
| **Learning** | Per-session | Continuous (feedback loop) |
| **Custom KB** | No | Yes (company-specific) |
| **Proven Solutions** | No | Yes (from ServiceNow) |
| **Deployment** | ✅ Production ready | 🔄 Optional add-on |

---

**Last Updated**: October 12, 2025  
**Version**: 7.0.0  
**Cluster**: loki123.orwi.p3.openshiftapps.com

`