# AI Troubleshooter v8 - NVIDIA Hybrid Retrieval Approach

## 🎯 Overview

This implementation follows **NVIDIA's exact approach** for log analysis from their GenerativeAIExamples repository, adapted for OpenShift/Kubernetes environments.

## 🏗️ Architecture

```
User Query + Namespace/Pod Selection
           ↓
    K8sLogFetcher
    (fetch logs from OpenShift using oc logs)
           ↓
    K8sHybridRetriever
    ├── Chunk logs (20K chars, 50% overlap)
    ├── Build BM25 index (in-memory)
    ├── Build FAISS index (in-memory, Granite embeddings)
    └── Combine with EnsembleRetriever (RRF)
           ↓
    Retrieve top-K relevant logs
           ↓
    LLM (Llama 3.2 3B) generates answer
           ↓
    Display to user
           ↓
    Discard indexes (ephemeral)
```

## 🆚 Key Differences from Previous Implementation

| Aspect | v7 (Old) | v8 NVIDIA (New) |
|--------|----------|-----------------|
| **Vector Storage** | Persistent Milvus | In-memory FAISS |
| **Data Lifecycle** | Pre-index → Query | Fetch → Index → Query → Discard |
| **Code Complexity** | ~300 lines | ~45 lines (core retriever) |
| **Dependencies** | Milvus, Llama Stack, LangGraph | LangChain only |
| **RRF Implementation** | Manual (60 lines) | Built-in (EnsembleRetriever) |
| **Chunking** | Unclear | 20K chars, 50% overlap |
| **Embeddings** | Granite via Llama Stack | Granite via Llama Stack |
| **Use Case** | Continuous monitoring | On-demand investigation |

## 📁 File Structure

```
ai-troubleshooter-v8/
├── k8s_log_fetcher.py              # Fetches logs from OpenShift
├── k8s_hybrid_retriever.py         # NVIDIA-style hybrid retrieval
├── v8_streamlit_nvidia_app.py      # Streamlit UI
├── deploy-nvidia-approach.sh       # Deployment script
├── test_nvidia_approach.py         # Test script
└── NVIDIA_APPROACH_GUIDE.md        # This file
```

## 🚀 Quick Start

### 1. Deploy to OpenShift

```bash
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v8"
./deploy-nvidia-approach.sh
```

### 2. Access the App

```bash
# Get the route URL
oc get route ai-troubleshooter-v8-nvidia -n ai-troubleshooter-v8

# Open in browser
# https://<route-url>
```

### 3. Use the App

1. **Enter Namespace**: e.g., `test-problematic-pods`
2. **Enter Pod Name**: e.g., `crash-loop-app-5466c959d4-dclps`
3. **Click "Load Logs & Create Retriever"**
   - Fetches logs from OpenShift
   - Chunks into 20K character segments with 50% overlap
   - Builds BM25 index (keyword search)
   - Builds FAISS index (semantic search with Granite embeddings)
   - Creates hybrid retriever with RRF
4. **Ask Questions**: e.g., "Why is this pod crashing?"
5. **Get Answers**: AI analyzes logs and provides actionable insights

## 🔧 Components

### 1. K8sLogFetcher (`k8s_log_fetcher.py`)

**Purpose**: Fetch logs from OpenShift pods using `oc logs` commands

**Key Methods**:
- `fetch_pod_logs(namespace, pod_name, tail)`: Get logs from single pod
- `fetch_namespace_logs(namespace, label_selector)`: Get logs from all pods in namespace
- `fetch_logs_as_text(...)`: Get concatenated logs ready for chunking

**Example**:
```python
fetcher = K8sLogFetcher(use_oc=True)
logs = fetcher.fetch_logs_as_text(
    namespace="test-problematic-pods",
    pod_name="crash-loop-app-5466c959d4-dclps",
    tail=5000
)
```

### 2. K8sHybridRetriever (`k8s_hybrid_retriever.py`)

**Purpose**: NVIDIA-style hybrid retrieval (BM25 + FAISS + RRF)

**Architecture** (exactly following NVIDIA):
```python
class K8sHybridRetriever:
    def __init__(self, log_content, llama_stack_url):
        # 1. Chunk logs (NVIDIA's settings)
        self.doc_splits = RecursiveCharacterTextSplitter(
            chunk_size=20000,      # 20K chars
            chunk_overlap=10000    # 50% overlap
        ).split_documents([log_content])
        
        # 2. Build BM25 index
        self.bm25_retriever = BM25Retriever.from_documents(self.doc_splits)
        
        # 3. Build FAISS index with Granite embeddings
        self.faiss_retriever = FAISS.from_documents(
            self.doc_splits,
            GraniteEmbeddings(llama_stack_url)
        ).as_retriever()
        
        # 4. Combine with RRF (LangChain's built-in)
        self.hybrid_retriever = EnsembleRetriever(
            retrievers=[self.bm25_retriever, self.faiss_retriever],
            weights=[0.5, 0.5]  # Equal weights (50/50)
        )
    
    def retrieve(self, query, k=5):
        # RRF happens automatically inside EnsembleRetriever
        return self.hybrid_retriever.get_relevant_documents(query)[:k]
```

**Key Features**:
- ✅ In-memory (no persistent DB)
- ✅ Ephemeral (built per request, discarded after)
- ✅ RRF via LangChain (automatic)
- ✅ NVIDIA's proven chunking strategy

### 3. Streamlit App (`v8_streamlit_nvidia_app.py`)

**Purpose**: User interface for log analysis

**Workflow**:
1. User selects namespace and pod
2. App fetches logs using K8sLogFetcher
3. App creates K8sHybridRetriever
4. User asks questions in chat
5. App retrieves relevant logs
6. LLM generates answer
7. Display results with metadata

## 📊 NVIDIA's Approach vs Ours

### What We Copied from NVIDIA:

1. ✅ **Chunking Strategy**: 20K chars, 50% overlap
2. ✅ **Hybrid Retrieval**: BM25 + FAISS
3. ✅ **RRF**: LangChain's EnsembleRetriever
4. ✅ **In-Memory**: FAISS (not persistent)
5. ✅ **Ephemeral**: Build → Use → Discard
6. ✅ **Equal Weights**: 50/50 for BM25 and FAISS

### What We Adapted for OpenShift:

1. 🔄 **Data Source**: NVIDIA uses file upload, we fetch from OpenShift
2. 🔄 **Embeddings**: NVIDIA uses NVIDIA API, we use Granite 125M via Llama Stack
3. 🔄 **UI**: NVIDIA uses basic Streamlit, we have enhanced chat interface
4. 🔄 **Context**: NVIDIA for general logs, we focus on K8s/OpenShift patterns

## 🎯 Use Cases

### Perfect For:
- ✅ **Alert Investigation**: Got an alert, need to investigate specific pod
- ✅ **On-Demand Analysis**: Ad-hoc troubleshooting
- ✅ **Fresh Data**: Always analyzes latest logs
- ✅ **Simple Infrastructure**: No vector DB to maintain

### Not Ideal For:
- ❌ **Historical Analysis**: Can't query old logs (ephemeral)
- ❌ **Pattern Detection**: Can't find patterns across time
- ❌ **Continuous Monitoring**: Need to rebuild index each time

## 🧪 Testing

### Local Test (without K8s):
```bash
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v8"
python3 test_nvidia_approach.py
```

### With K8s Access:
```bash
python3 test_nvidia_approach.py
# When prompted, type 'y' to test log fetcher
```

## 🔍 Example Queries

1. **OOM Errors**: "Why is my pod getting OOMKilled?"
2. **Image Pull**: "Why can't my pod pull the container image?"
3. **Crash Loops**: "What's causing the crash loop?"
4. **Network Issues**: "Are there any network connectivity problems?"
5. **Performance**: "Is the application responding slowly?"

## 📈 Performance

- **Chunking**: ~1-2 seconds for 10K lines of logs
- **BM25 Indexing**: ~0.5 seconds
- **FAISS Indexing**: ~2-3 seconds (embedding generation)
- **Query**: ~1-2 seconds
- **Total First Query**: ~5-8 seconds
- **Subsequent Queries**: ~1-2 seconds (indexes cached)

## 🐛 Troubleshooting

### "Failed to fetch logs"
- Check RBAC: `oc auth can-i get pods --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa`
- Check namespace exists: `oc get namespace <namespace>`
- Check pod exists: `oc get pod <pod-name> -n <namespace>`

### "Embedding error"
- Check Llama Stack is running: `oc get pods -n ai-troubleshooter-v8 | grep llama-stack`
- Check embedding model is loaded: `curl http://llama-stack-service:8321/models`

### "No relevant logs found"
- Check logs are not empty
- Try more specific questions
- Check pod has sufficient logs (use larger `tail` value)

## 📚 References

- **NVIDIA Repository**: https://github.com/NVIDIA/GenerativeAIExamples/tree/main/community/log_analysis_multi_agent_rag
- **NVIDIA's Implementation**: `multiagent.py` (HybridRetriever class)
- **LangChain EnsembleRetriever**: https://python.langchain.com/docs/modules/data_connection/retrievers/ensemble
- **FAISS**: https://github.com/facebookresearch/faiss

## 🎉 Summary

This implementation is a **direct adaptation** of NVIDIA's proven log analysis approach:
- ✅ Same chunking strategy (20K/50%)
- ✅ Same hybrid approach (BM25 + FAISS)
- ✅ Same RRF method (EnsembleRetriever)
- ✅ Same ephemeral design (build → use → discard)

**Result**: Simple, effective, and proven! 🚀


