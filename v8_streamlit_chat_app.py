#!/usr/bin/env python3
"""
AI Troubleshooter v8 - Chat Interface
Multi-Agent RAG with conversational chat interface
"""

import streamlit as st
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import sys

# Add v7 modules to path
sys.path.insert(0, os.path.dirname(__file__))

# Import v7 multi-agent components
try:
    from v7_main_graph import create_workflow, run_analysis
    from v7_state_schema import GraphState
    from llama_stack_client import LlamaStackClient
except ImportError as e:
    st.error(f"Failed to import required modules: {e}")
    st.error("Make sure all v7 modules are present in the ConfigMap.")
    st.stop()

# Configuration
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321")
LLAMA_STACK_MODEL = os.getenv("LLAMA_STACK_MODEL", "llama-32-3b-instruct")
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "openshift-logs-v8")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
BGE_RERANKER_URL = os.getenv("BGE_RERANKER_URL", "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com")

# Kubernetes Data Collector
class KubernetesDataCollector:
    """Collects data from OpenShift/Kubernetes cluster"""
    
    def __init__(self):
        self.use_mcp = False  # Use oc commands
        self.data_source = "oc commands"
        
    def get_namespaces(self):
        try:
            result = subprocess.run(['oc', 'get', 'namespaces', '--no-headers'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return [line.split()[0] for line in result.stdout.strip().split('\n') if line.strip()]
        except:
            pass
        return ["default"]
    
    def get_pods_in_namespace(self, namespace: str):
        try:
            result = subprocess.run(['oc', 'get', 'pods', '-n', namespace, '--no-headers'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                pods = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split()
                        if parts:
                            pods.append(parts[0])
                return pods
        except:
            pass
        return []
    
    def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 100):
        try:
            result = subprocess.run(['oc', 'logs', pod_name, '-n', namespace, f'--tail={tail_lines}'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_events(self, namespace: str):
        """Get ALL events from namespace (use for namespace-wide analysis)"""
        try:
            result = subprocess.run(['oc', 'get', 'events', '-n', namespace, '--sort-by=.lastTimestamp'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_events(self, pod_name: str, namespace: str):
        """Get events ONLY for specific pod (CRITICAL for single-pod analysis)"""
        try:
            result = subprocess.run([
                'oc', 'get', 'events', '-n', namespace,
                f'--field-selector=involvedObject.name={pod_name}',
                '--sort-by=.lastTimestamp'
            ], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_info(self, pod_name: str, namespace: str):
        try:
            result = subprocess.run(['oc', 'get', 'pod', pod_name, '-n', namespace, '-o', 'json'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return {}
    
    def get_pod_describe(self, pod_name: str, namespace: str):
        """Get complete pod description (CRITICAL for full context)"""
        try:
            result = subprocess.run(['oc', 'describe', 'pod', pod_name, '-n', namespace], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_pod_status(self, pod_name: str, namespace: str):
        """Get quick pod status"""
        try:
            result = subprocess.run(['oc', 'get', 'pod', pod_name, '-n', namespace, '--no-headers'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 3:
                    return {"name": parts[0], "ready": parts[1], "status": parts[2]}
        except:
            pass
        return {}

# Initialize components
if 'k8s_collector' not in st.session_state:
    st.session_state.k8s_collector = KubernetesDataCollector()

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Initialize context
if 'current_namespace' not in st.session_state:
    st.session_state.current_namespace = None
if 'current_pod' not in st.session_state:
    st.session_state.current_pod = None
if 'current_context' not in st.session_state:
    st.session_state.current_context = {}

# Page configuration
st.set_page_config(
    page_title="AI Troubleshooter v8 - Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with proper contrast
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6, #10b981);
        color: white !important;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1rem;
        border: 1px solid #3b82f6;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
    }
    
    .chat-header {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: bold;
        margin: 0.5rem 0;
        text-align: center;
    }
    
    .context-badge {
        background: #f0f9ff;
        color: #0c4a6e;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
        font-size: 0.85rem;
    }
    
    /* User message styling - Blue background with white text */
    [data-testid="stChatMessageContent"][data-testid*="user"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) {
        background-color: #3b82f6 !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid*="user"]) span {
        color: white !important;
    }
    
    /* Assistant message styling - Light gray background with dark text */
    [data-testid="stChatMessageContent"][data-testid*="assistant"] {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) {
        background-color: #f1f5f9 !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
        border-left: 4px solid #10b981 !important;
    }
    
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) div,
    div[data-testid="stChatMessage"]:has(div[data-testid*="assistant"]) span {
        color: #1e293b !important;
    }
    
    /* Alternative selectors for user messages */
    .stChatMessage.user {
        background-color: #3b82f6 !important;
        border-radius: 15px;
        padding: 1rem;
    }
    
    .stChatMessage.user * {
        color: white !important;
    }
    
    /* Alternative selectors for assistant messages */
    .stChatMessage.assistant {
        background-color: #f1f5f9 !important;
        border-radius: 15px;
        padding: 1rem;
        border-left: 4px solid #10b981;
    }
    
    .stChatMessage.assistant * {
        color: #1e293b !important;
    }
    
    /* Broad selector for all chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 15px !important;
        padding: 1rem !important;
        margin: 0.5rem 0 !important;
    }
    
    /* Chat message content */
    [data-testid="stChatMessageContent"] {
        padding: 0.5rem !important;
    }
    
    /* Chat input styling - Dark to match chat bubbles */
    [data-testid="stChatInput"] {
        background-color: #1e293b !important;
    }
    
    [data-testid="stChatInput"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    [data-testid="stChatInput"] textarea {
        background-color: #1e293b !important;
        color: #ffffff !important;
    }
    
    /* Input placeholder text */
    [data-testid="stChatInput"] input::placeholder,
    [data-testid="stChatInput"] textarea::placeholder {
        color: #94a3b8 !important;
    }
    
    /* Ensure readable text */
    .main .block-container {
        color: #1e293b;
    }
    
    /* Avatar styling for better contrast */
    [data-testid="chatAvatarIcon-user"] {
        background-color: #ef4444 !important;
    }
    
    [data-testid="chatAvatarIcon-assistant"] {
        background-color: #f97316 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>💬 AI Troubleshooter v8 - Chat Interface</h1>
    <p>Chat with your OpenShift cluster | Multi-Agent RAG with BGE Reranker</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔧 Configuration")
    
    # Data source info
    st.info(f"🔵 **Data Source**: {st.session_state.k8s_collector.data_source}")
    st.info(f"🤖 **AI Model**: {LLAMA_STACK_MODEL}")
    st.info(f"🎯 **BGE Reranker**: Enabled")
    
    st.markdown("---")
    st.markdown("## 📍 Context Selection")
    
    # Namespace selection
    namespaces = st.session_state.k8s_collector.get_namespaces()
    selected_namespace = st.selectbox(
        "📁 Namespace:",
        options=namespaces,
        index=namespaces.index(st.session_state.current_namespace) if st.session_state.current_namespace in namespaces else 0,
        key="namespace_selector"
    )
    
    # Update namespace context
    if selected_namespace != st.session_state.current_namespace:
        st.session_state.current_namespace = selected_namespace
        st.session_state.current_pod = None  # Reset pod when namespace changes
    
    # Pod selection
    if selected_namespace:
        pods = st.session_state.k8s_collector.get_pods_in_namespace(selected_namespace)
        
        pod_options = ["All Pods (Namespace-wide)"] + (pods if pods else ["No pods found"])
        
        default_index = 0
        if st.session_state.current_pod and st.session_state.current_pod in pods:
            default_index = pods.index(st.session_state.current_pod) + 1
        
        selected_pod = st.selectbox(
            "🐳 Pod:",
            options=pod_options,
            index=default_index,
            key="pod_selector"
        )
        
        if selected_pod != "All Pods (Namespace-wide)" and selected_pod != "No pods found":
            st.session_state.current_pod = selected_pod
        else:
            st.session_state.current_pod = None
    
    st.markdown("---")
    st.markdown("## 🎛️ Options")
    
    include_logs = st.checkbox("📝 Include Recent Logs", value=True)
    include_events = st.checkbox("📋 Include Events", value=True)
    max_iterations = st.slider("🔄 Max Iterations", 1, 5, MAX_ITERATIONS)
    
    st.markdown("---")
    
    # Clear chat button
    st.markdown("### 🔄 Context Management")
    st.info("💡 **Tip**: Clear history for fresh start, or keep it for follow-up questions")
    if st.button("🗑️ Clear Chat History & Start Fresh", use_container_width=True):
        st.session_state.messages = []
        st.success("✅ Chat cleared! Next question will start fresh.")
        st.rerun()
    
    # Quick examples
    st.markdown("### 💡 Example Questions")
    st.markdown("""
    - Why is my pod failing?
    - What errors are in the logs?
    - Is the pod OOMKilled?
    - Show me recent events
    - What's causing the restart?
    """)

# Main chat interface
st.markdown("## 💬 Chat with AI Troubleshooter")

# Display current context
if st.session_state.current_namespace:
    context_text = f"📍 **Context**: Namespace `{st.session_state.current_namespace}`"
    if st.session_state.current_pod:
        context_text += f" → Pod `{st.session_state.current_pod}`"
    st.markdown(f'<div class="context-badge">{context_text}</div>', unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Show metadata if present
        if "metadata" in message:
            with st.expander("📊 Analysis Details"):
                st.json(message["metadata"])

# Chat input
if prompt := st.chat_input("Ask about your pods, logs, or cluster issues..."):
    # Check if context is set
    if not st.session_state.current_namespace:
        st.error("❌ Please select a namespace first!")
        st.stop()
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("🤖 Analyzing..."):
            try:
                # Collect context data
                namespace = st.session_state.current_namespace
                pod_name = st.session_state.current_pod
                
                # CRITICAL FIX: Augment user query with selected namespace and pod
                # This ensures retrieval focuses on the correct pod
                augmented_query = prompt
                if pod_name:
                    # Add pod and namespace to query for better retrieval
                    augmented_query = f"{prompt} [Context: analyzing pod '{pod_name}' in namespace '{namespace}']"
                else:
                    # Namespace-wide query
                    augmented_query = f"{prompt} [Context: analyzing namespace '{namespace}']"
                
                # Gather logs and events
                logs = ""
                events = ""
                
                if pod_name:
                    # Specific pod analysis - ONLY this pod!
                    if include_logs:
                        logs = st.session_state.k8s_collector.get_pod_logs(pod_name, namespace, tail_lines=100)
                    if include_events:
                        # CRITICAL FIX: Filter events by specific pod, not entire namespace!
                        events = st.session_state.k8s_collector.get_pod_events(pod_name, namespace)
                    
                    # CRITICAL: Always include pod describe for complete context
                    pod_describe = st.session_state.k8s_collector.get_pod_describe(pod_name, namespace)
                    logs = f"{pod_describe}\n\n=== Pod Logs ===\n{logs}"
                else:
                    # Namespace-wide analysis
                    if include_events:
                        events = st.session_state.k8s_collector.get_events(namespace)
                    if include_logs:
                        # Get logs from first few pods
                        pods = st.session_state.k8s_collector.get_pods_in_namespace(namespace)
                        log_parts = []
                        for p in pods[:3]:  # First 3 pods
                            pod_logs = st.session_state.k8s_collector.get_pod_logs(p, namespace, tail_lines=30)
                            if pod_logs:
                                log_parts.append(f"=== Pod: {p} ===\n{pod_logs}\n")
                        logs = "\n".join(log_parts)
                
                # Run multi-agent analysis with augmented query
                result = run_analysis(
                    question=augmented_query,
                    namespace=namespace,
                    pod_name=pod_name or "",
                    log_context=logs,
                    pod_events=events,
                    llama_stack_url=LLAMA_STACK_URL,
                    max_iterations=max_iterations,
                    vector_db_id=VECTOR_DB_ID,
                    reranker_url=BGE_RERANKER_URL
                )
                
                # Extract answer
                if result and "answer" in result:
                    answer = result["answer"]
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Prepare metadata
                    metadata = {
                        "namespace": namespace,
                        "pod": pod_name or "All Pods",
                        "iterations": result.get("iterations", 1),
                        "docs_retrieved": result.get("metadata", {}).get("num_docs_retrieved", 0),
                        "docs_reranked": result.get("metadata", {}).get("num_docs_relevant", 0),
                        "timestamp": result.get("timestamp", datetime.now().isoformat())
                    }
                    
                    # Add assistant message to chat
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "metadata": metadata
                    })
                    
                else:
                    error_msg = "❌ Analysis failed. Please try again."
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
            except Exception as e:
                error_msg = f"❌ Error during analysis: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"🤖 Model: {LLAMA_STACK_MODEL}")
with col2:
    st.caption(f"💬 Messages: {len(st.session_state.messages)}")
with col3:
    st.caption(f"📍 Context: {st.session_state.current_namespace or 'Not set'}")

