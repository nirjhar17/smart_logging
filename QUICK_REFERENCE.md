# 🎯 AI Troubleshooter v7 - Quick Reference

**One-page cheat sheet for v7 operations**

---

## 📍 Access Information

**URL**: `https://ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123.orwi.p3.openshiftapps.com`

**Namespace**: `ai-troubleshooter-v7`

**ServiceAccount**: `ai-troubleshooter-v7-sa` (read-only cluster access)

---

## 🚀 Quick Commands

### Check Status
```bash
# Pod status
oc get pods -n ai-troubleshooter-v7

# Pod logs
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --tail=100

# Route URL
oc get route ai-troubleshooter-v7 -n ai-troubleshooter-v7 -o jsonpath='https://{.spec.host}'

# Test connectivity
curl -I https://ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123.orwi.p3.openshiftapps.com
```

### Restart/Update
```bash
# Restart pod
oc delete pod -l app=ai-troubleshooter-v7 -n ai-troubleshooter-v7

# Update code
oc delete configmap ai-troubleshooter-v7-code -n ai-troubleshooter-v7
oc create configmap ai-troubleshooter-v7-code \
  --from-file=app.py=v7_streamlit_app.py \
  --from-file=state_schema.py=v7_state_schema.py \
  --from-file=hybrid_retriever.py=v7_hybrid_retriever.py \
  --from-file=graph_nodes.py=v7_graph_nodes.py \
  --from-file=graph_edges.py=v7_graph_edges.py \
  --from-file=main_graph.py=v7_main_graph.py \
  --from-file=log_collector.py=v7_log_collector.py \
  -n ai-troubleshooter-v7
oc delete pod -l app=ai-troubleshooter-v7 -n ai-troubleshooter-v7
```

### Troubleshooting
```bash
# Check events
oc get events -n ai-troubleshooter-v7 --sort-by=.lastTimestamp

# Verify RBAC
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- oc get namespaces --no-headers | wc -l
# Should return: 116

# Test Llama Stack
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- \
  curl -s http://llamastack-custom-distribution-service.model.svc.cluster.local:8321/v1/health
```

---

## 🏗️ Architecture Quick View

```
User Browser
    ↓ HTTPS
[Route (TLS Edge)]
    ↓
[Service :8501]
    ↓
[Pod: Streamlit + Python 3.11]
    ├─ KubernetesDataCollector (oc commands via ServiceAccount)
    ├─ LangGraph Workflow
    │   ├─ RETRIEVE (BM25 + Milvus)
    │   ├─ RERANK (score-based)
    │   ├─ GRADE (LLM relevance check)
    │   ├─ GENERATE (LLM analysis)
    │   └─ TRANSFORM (query rewriting)
    └─ HybridRetriever (BM25Okapi + Llama Stack)
        ↓
[Llama Stack @ model namespace]
    ├─ LLM: Llama 3.2 3B
    ├─ Embeddings: Granite 125M
    └─ (Optional) Milvus Vector DB
```

---

## 🎯 Multi-Agent Workflow

```
1. RETRIEVE
   ├─ Build BM25 index from logs
   ├─ BM25 search (keyword matching)
   ├─ Milvus search (semantic, optional)
   └─ RRF fusion → Top 10 docs

2. RERANK
   └─ Sort by score → Top 5

3. GRADE
   ├─ LLM grades each doc (0.0-1.0)
   └─ Keep if score ≥ 0.6

4. GENERATE
   └─ LLM creates troubleshooting answer

5. EVALUATE
   ├─ Is answer good? → END
   └─ Not good? → TRANSFORM QUERY → Retry (max 3x)
```

---

## 📊 Key Features

| Feature | Implementation |
|---------|----------------|
| **Retrieval** | Hybrid (BM25 + Milvus) |
| **Self-Correction** | Up to 3 iterations |
| **Orchestration** | LangGraph state machine |
| **LLM** | Llama 3.2 3B Instruct |
| **Embeddings** | Granite 125M (768D) |
| **Auth** | RBAC + ServiceAccount |
| **Python** | 3.11 (modern type hints) |
| **Frontend** | Streamlit (6 tabs) |

---

## 🔧 Common Issues & Fixes

### Issue: Pod CrashLoopBackOff
```bash
# Check logs
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --previous

# Common causes:
# 1. Missing dependency → Add to pip install command
# 2. Python syntax error → Check ConfigMap files
# 3. Port conflict → Verify 8501 is free
```

### Issue: Route Returns 503
```bash
# Check pod is running
oc get pods -n ai-troubleshooter-v7

# If not running, check why
oc describe pod -n ai-troubleshooter-v7 -l app=ai-troubleshooter-v7

# Restart if needed
oc delete pod -l app=ai-troubleshooter-v7 -n ai-troubleshooter-v7
```

### Issue: No Namespaces Showing
```bash
# Verify RBAC
oc get clusterrolebinding ai-troubleshooter-v7-binding

# Test permissions
oc auth can-i list namespaces --as=system:serviceaccount:ai-troubleshooter-v7:ai-troubleshooter-v7-sa
# Should return: yes
```

### Issue: BM25 Index Not Building
```bash
# Check logs for "Building BM25 index"
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 | grep "BM25"

# Should see:
# 📊 Building BM25 index from 12345 chars of logs...
# 📄 Created 103 document chunks from logs
# ✅ BM25 index built with 103 documents

# If missing, code needs update (already fixed in latest version)
```

---

## 📝 Usage Flow

### Step 1: Access UI
Open: `https://ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123.orwi.p3.openshiftapps.com`

### Step 2: Select Target
- **Namespace**: Choose from dropdown (116 available)
- **Pod**: Choose from dropdown (auto-populates)

### Step 3: Configure
- ✅ Include Recent Logs (recommended)
- ✅ Include Pod Events (recommended)
- 🔄 Max Iterations: 3 (default)

### Step 4: Analyze
Click **🚀 Start Multi-Agent Deep Analysis**

### Step 5: Review
- **Tab 1**: Multi-Agent Analysis (main recommendations)
- **Tab 2**: Evidence (relevant log snippets)
- **Tab 3**: Workflow (execution trace)
- **Tab 4**: Pod Details
- **Tab 5**: Metrics
- **Tab 6**: Storage Check

---

## 🎓 Key Concepts

### BM25 (Lexical Search)
- **What**: Keyword matching algorithm
- **Good for**: Exact error codes, pod names, specific strings
- **Example**: "ImagePullBackOff", "HTTP 503", "OOMKilled"

### Milvus (Semantic Search)
- **What**: Vector similarity search
- **Good for**: Conceptual matches, paraphrases
- **Example**: "crashed" matches "terminated", "failed", "stopped"

### Hybrid Retrieval
- **What**: Combines BM25 + Milvus using RRF
- **Why**: Best of both worlds (precision + recall)
- **RRF**: `score(doc) = Σ[1 / (k + rank)]`

### Self-Correction
- **What**: Automatic query rewriting on failure
- **How**: If no relevant docs → Transform query → Retry
- **Max**: 3 iterations to avoid infinite loops

### LangGraph
- **What**: State machine for multi-agent workflows
- **Why**: Transparent, debuggable, modular
- **State**: Shared across all agents (retrieve, rerank, grade, generate)

---

## 📊 Performance

```
Average Analysis Time: 5-15 seconds

Breakdown:
├─ Data Collection:  1-2 sec (oc commands)
├─ BM25 Indexing:    200-500 ms
├─ Per Iteration:    2-4 sec
│  ├─ Retrieve:      500 ms
│  ├─ Rerank:        100 ms
│  ├─ Grade:         1-2 sec (LLM calls)
│  └─ Generate:      1-2 sec (LLM)
└─ Rendering:        500 ms

Resources:
├─ CPU:    250m request, 1 core limit
├─ Memory: 512Mi request, 2Gi limit
└─ Concurrent: 1-2 analyses per pod
```

---

## 🔒 Security

### RBAC Permissions (Read-Only)
```yaml
ClusterRole: ai-troubleshooter-v7-reader
Can:
  ✅ List/get namespaces, pods, events, PVCs
  ✅ Read pod logs
  ✅ List deployments, services, routes
Cannot:
  ❌ Create/delete/update any resources
  ❌ Execute commands in pods (except via ServiceAccount)
  ❌ Access secrets
```

### Network
- **Inbound**: HTTPS only (TLS edge termination)
- **Outbound**: Llama Stack API (internal only)
- **No**: External API calls, internet access

---

## 📂 File Locations

```
Local (Development):
/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v7/

OpenShift (Runtime):
/tmp/                      # Application code (copied from ConfigMap)
/app-config/              # ConfigMap mount point
~/.kube/config            # Auto-generated by ServiceAccount
~/bin/oc                  # OpenShift CLI
```

---

## 🔗 Related Resources

- **v6 (Previous)**: `ai-troubleshooter-v6` namespace
- **Llama Stack**: `model` namespace, `llamastack-custom-distribution-service`
- **LLM**: `model` namespace, `llama-32-3b-instruct-predictor`
- **MCP Server**: `model` namespace, `ocp-mcp-server`

---

## 📞 Quick Debugging

```bash
# Is pod running?
oc get pods -n ai-troubleshooter-v7

# What's in the logs?
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --tail=50

# Can pod access cluster?
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- oc get ns | head -5

# Can reach Llama Stack?
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- \
  curl -s http://llamastack-custom-distribution-service.model.svc.cluster.local:8321/v1/health | python -m json.tool

# Route working?
curl -I https://ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123.orwi.p3.openshiftapps.com
```

---

## 🎯 Success Indicators

✅ **Pod Status**: `1/1 Running`  
✅ **Route HTTP**: `200 OK`  
✅ **Logs**: `You can now view your Streamlit app`  
✅ **RBAC**: Can list 116 namespaces  
✅ **Llama Stack**: Returns `{"status":"healthy"}`  
✅ **Analysis**: Retrieves >0 documents, generates answer

---

**Last Updated**: October 12, 2025  
**Version**: 7.0.0  
**Cluster**: loki123.orwi.p3.openshiftapps.com

