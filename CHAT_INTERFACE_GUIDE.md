# AI Troubleshooter v8 - Chat Interface Guide

## 🎯 Overview

The new chat interface (`v8_streamlit_chat_app.py`) provides a **conversational way** to interact with your OpenShift cluster. Instead of clicking buttons, you can now chat naturally with the AI troubleshooter.

## ✨ Key Features

### 💬 **Chat-Based Interaction**
- Natural conversation with AI
- Ask questions in plain English
- Get instant analysis and troubleshooting
- Chat history preserved during session

### 📍 **Context-Aware**
- Select namespace and pod from sidebar
- AI maintains context across questions
- Can analyze specific pods or entire namespaces

### 🤖 **Full Multi-Agent RAG**
- Uses same powerful v8 engine
- BGE reranker integration
- Hybrid retrieval (BM25 + Vector)
- Self-corrective iterations

### 💡 **Smart Response**
- Relevant log snippets
- Root cause analysis
- Actionable recommendations
- Analysis metadata

## 🚀 Getting Started

### 1. **Select Your Context**

In the sidebar:
1. Choose a **Namespace** (e.g., `ai-troubleshooter-v8`, `model`, `default`)
2. Choose a **Pod** or select "All Pods (Namespace-wide)"
3. Toggle options:
   - ✅ Include Recent Logs
   - ✅ Include Events

### 2. **Ask Questions**

Type naturally in the chat input. Examples:

#### 🔍 **General Questions**
```
Why is my pod failing?
What's wrong with this pod?
Show me the errors
Is there an OOM issue?
```

#### 📊 **Specific Queries**
```
What errors are in the logs?
Why is the pod restarting?
Is there a network issue?
What's causing ImagePullBackOff?
```

#### 🎯 **Troubleshooting**
```
How do I fix this OOMKilled error?
What's the root cause of the crash?
Why can't the pod pull the image?
What resources is the pod using?
```

### 3. **View Results**

The AI responds with:
- 🚨 **Issue Summary**
- 📋 **Root Cause**
- ⚡ **Immediate Actions**
- 🔧 **Resolution Steps**

Click **"📊 Analysis Details"** to see:
- Number of documents retrieved
- Reranking scores
- Iterations performed
- Timestamp

## 📝 Example Conversation

```
You: Why is my pod in CrashLoopBackOff?

AI: 🚨 **ISSUE**: Pod experiencing CrashLoopBackOff due to application startup failure

📋 **ROOT CAUSE**: Based on log evidence, the pod is failing to start because:
- Exit code 137 indicates OOMKilled (out of memory)
- Container requested 2Gi but limit is set to 1Gi
- Memory usage exceeded limit during startup

⚡ **IMMEDIATE ACTIONS**:
```bash
# Check current resource limits
oc describe pod <pod-name> -n <namespace>

# View memory usage
oc adm top pod <pod-name> -n <namespace>
```

🔧 **RESOLUTION**:
1. Increase memory limit in deployment:
   ```yaml
   resources:
     limits:
       memory: 2Gi
   ```
2. Apply changes: `oc apply -f deployment.yaml`
3. Monitor: `oc get pods -w`

You: How do I check if it's fixed?

AI: To verify the fix:
1. Watch pod status: `oc get pods -n <namespace> -w`
2. Check events: `oc get events --sort-by=.lastTimestamp`
3. Monitor logs: `oc logs -f <pod-name>`

Look for:
✅ Pod status changes to "Running"
✅ Ready count shows "1/1"
✅ No restart count increases
```

## 🎛️ Configuration Options

### Sidebar Controls

| Option | Description | Default |
|--------|-------------|---------|
| **Include Recent Logs** | Fetch last 100 lines of pod logs | ✅ On |
| **Include Events** | Fetch namespace events | ✅ On |
| **Max Iterations** | Self-correction loops (1-5) | 3 |

### Context Selection

- **Namespace**: Required - Select cluster namespace
- **Pod**: Optional
  - Select specific pod for targeted analysis
  - Or choose "All Pods" for namespace-wide view

## 💡 Pro Tips

### 1. **Start Broad, Then Narrow**
```
You: What issues are in the ai-troubleshooter-v8 namespace?
[AI provides overview]

You: Tell me more about the pod ai-app-123
[Switch pod in sidebar, ask follow-up]
```

### 2. **Use Context Switching**
Change namespace/pod in sidebar without losing chat history. Perfect for investigating related issues across multiple pods.

### 3. **Ask Follow-Up Questions**
The chat maintains context:
```
You: Why is the pod failing?
AI: [Analysis about OOM error]

You: How do I increase the memory?
AI: [Specific steps to update resources]

You: What should I monitor after the change?
AI: [Monitoring recommendations]
```

### 4. **Request Specific Information**
```
You: Show me only ERROR lines from the logs
You: What happened in the last 5 minutes?
You: Are there any security issues?
You: Compare this pod to the working one
```

## 🔄 Comparison: Old vs New Interface

### Old Button-Based UI
- Click "Analyze"
- Wait for results
- Single analysis per click
- No follow-up questions

### New Chat Interface
- Type naturally
- Continuous conversation
- Multiple related queries
- Context-aware responses
- Chat history

## 🚀 Deployment

### Option 1: Replace Existing App

Update the ConfigMap to use chat interface:

```bash
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v8"

# Create configmap with chat app
oc create configmap ai-troubleshooter-v8-code \
  --from-file=app.py=v8_streamlit_chat_app.py \
  --from-file=v7_main_graph.py \
  --from-file=v7_graph_nodes.py \
  --from-file=v7_graph_edges.py \
  --from-file=v7_state_schema.py \
  --from-file=v7_hybrid_retriever.py \
  --from-file=v7_bge_reranker.py \
  --from-file=v7_log_collector.py \
  -n ai-troubleshooter-v8 \
  --dry-run=client -o yaml | oc apply -f -

# Restart to apply
oc rollout restart deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8
```

### Option 2: Run Side-by-Side

Deploy chat interface as separate service:

```bash
# Deploy as ai-troubleshooter-v8-chat
# Update deployment.yaml to use different name and route
```

### Option 3: Test Locally First

```bash
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v8"

# Set environment variables
export LLAMA_STACK_URL="http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
export BGE_RERANKER_URL="https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com"

# Run locally
streamlit run v8_streamlit_chat_app.py --server.port 8501
```

## 🎨 UI Features

### Chat Layout
- **Wide layout** for better readability
- **Sidebar** for context and controls
- **Main chat area** with user/assistant messages
- **Expandable details** for metadata

### Visual Indicators
- 💬 User messages in standard chat bubbles
- 🤖 AI responses with formatted markdown
- 📊 Expandable analysis details
- 📍 Context badge showing current namespace/pod

### Session Management
- Chat history preserved during session
- Clear button to start fresh
- Context switching without losing history

## 🐛 Troubleshooting

### Issue: "Please select a namespace first"
**Solution**: Select a namespace from the sidebar before asking questions.

### Issue: "No pods found"
**Solution**: 
- Check if namespace has running pods: `oc get pods -n <namespace>`
- Try different namespace
- Verify RBAC permissions

### Issue: Analysis takes too long
**Solution**:
- Reduce "Max Iterations" to 1-2
- Uncheck "Include Recent Logs" for faster response
- Select specific pod instead of "All Pods"

### Issue: Empty or generic responses
**Solution**:
- Make sure "Include Logs" and "Include Events" are checked
- Be more specific in your question
- Select a specific pod that has issues

## 📊 Chat Session Tips

### Clear Chat When:
- Switching to completely different issue
- Chat becomes too long (>20 messages)
- Want fresh start

### Keep Chat When:
- Investigating related issues
- Following troubleshooting steps
- Need to reference previous answers

## 🔒 Security Notes

- Service account has **read-only** cluster access
- No destructive operations possible
- Logs and events are temporarily cached
- Chat history not persisted between sessions

## 📚 Advanced Usage

### Multi-Pod Investigation
```
Context: Namespace = model, Pod = All Pods

You: Are any pods having issues?
AI: [Analyzes all pods in model namespace]

You: Focus on the bge-reranker pod
[Switch to specific pod in sidebar]

You: What's its status?
AI: [Detailed analysis of bge-reranker]
```

### Root Cause Analysis
```
You: Pod keeps restarting, find the root cause

AI: [Deep analysis with log correlation]

You: What's the fix?

AI: [Step-by-step resolution]

You: How do I prevent this in the future?

AI: [Best practices and recommendations]
```

## 🎯 Summary

The chat interface transforms AI Troubleshooter v8 into an **interactive debugging companion**. Instead of one-off analyses, you can now:

✅ Have natural conversations about your cluster
✅ Ask follow-up questions
✅ Get progressive insights
✅ Maintain context across multiple queries
✅ Troubleshoot interactively

**Start chatting with your cluster today!** 💬🚀


