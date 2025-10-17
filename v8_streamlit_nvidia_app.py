"""
AI Troubleshooter v8 - NVIDIA-Style Streamlit App
Implements NVIDIA's in-memory hybrid retrieval approach for OpenShift logs
"""

import os
import streamlit as st
import logging
from typing import Optional, Dict, List
from datetime import datetime
from k8s_log_fetcher import K8sLogFetcher
from k8s_hybrid_retriever import K8sHybridRetriever
from llama_stack_client import LlamaStackClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="AI Troubleshooter v8 - NVIDIA Approach",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    /* Main container */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Chat messages - User */
    .stChatMessage[data-testid="chat-message-user"] {
        background-color: #1e3a5f !important;
        border-left: 3px solid #4a90e2 !important;
        color: #ffffff !important;
    }
    
    .stChatMessage[data-testid="chat-message-user"] p {
        color: #ffffff !important;
    }
    
    /* Chat messages - Assistant */
    .stChatMessage[data-testid="chat-message-assistant"] {
        background-color: #1a472a !important;
        border-left: 3px solid #2ecc71 !important;
        color: #ffffff !important;
    }
    
    .stChatMessage[data-testid="chat-message-assistant"] p {
        color: #ffffff !important;
    }
    
    /* Chat input */
    .stChatInput textarea {
        background-color: #262730 !important;
        color: #ffffff !important;
        border: 1px solid #4a90e2 !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1a1a2e;
    }
    
    section[data-testid="stSidebar"] label {
        color: #ffffff !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #4a90e2 !important;
    }
    
    /* Success/Info boxes */
    .stSuccess, .stInfo {
        background-color: #1a472a !important;
        color: #ffffff !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #4a90e2 !important;
    }
</style>
""", unsafe_allow_html=True)

# Environment variables
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://llama-stack-service.ai-troubleshooter-v8.svc.cluster.local:8321")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "retriever" not in st.session_state:
    st.session_state.retriever = None
    
if "log_content" not in st.session_state:
    st.session_state.log_content = None
    
if "namespace" not in st.session_state:
    st.session_state.namespace = ""
    
if "pod_name" not in st.session_state:
    st.session_state.pod_name = ""


def fetch_namespaces() -> List[str]:
    """Fetch available namespaces"""
    try:
        import subprocess
        result = subprocess.run(
            ["oc", "get", "namespaces", "-o", "name"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            namespaces = [ns.replace("namespace/", "").strip() for ns in result.stdout.split("\n") if ns.strip()]
            return sorted(namespaces)
        return []
    except Exception as e:
        logger.error(f"Error fetching namespaces: {e}")
        return []


def fetch_pods(namespace: str) -> List[str]:
    """Fetch pods in namespace"""
    try:
        import subprocess
        result = subprocess.run(
            ["oc", "get", "pods", "-n", namespace, "-o", "name"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            pods = [pod.replace("pod/", "").strip() for pod in result.stdout.split("\n") if pod.strip()]
            return sorted(pods)
        return []
    except Exception as e:
        logger.error(f"Error fetching pods: {e}")
        return []


def load_logs_and_create_retriever(namespace: str, pod_name: str) -> bool:
    """
    Load logs from OpenShift and create hybrid retriever
    (NVIDIA's approach: fetch → chunk → index → ready)
    """
    try:
        with st.spinner("🔄 Fetching logs from OpenShift..."):
            log_fetcher = K8sLogFetcher(use_oc=True)
            log_content = log_fetcher.fetch_logs_as_text(
                namespace=namespace,
                pod_name=pod_name,
                tail=5000
            )
            
            if not log_content or len(log_content) < 100:
                st.error("❌ No logs found or logs too short")
                return False
                
            st.session_state.log_content = log_content
            
        with st.spinner("🔄 Building hybrid retriever (BM25 + FAISS + RRF)..."):
            retriever = K8sHybridRetriever(
                log_content=log_content,
                llama_stack_url=LLAMA_STACK_URL
            )
            st.session_state.retriever = retriever
            
        st.success(f"✅ Retriever ready! Loaded {len(log_content)} characters from pod logs")
        return True
        
    except Exception as e:
        logger.error(f"Error creating retriever: {e}", exc_info=True)
        st.error(f"❌ Error: {str(e)}")
        return False


def answer_question(query: str) -> Dict:
    """
    Answer user question using hybrid retrieval + LLM
    """
    try:
        # Retrieve relevant logs
        retriever = st.session_state.retriever
        documents = retriever.retrieve(query, k=5)  # Focus on most relevant chunks
        
        if not documents:
            return {
                "answer": "No relevant logs found for your query.",
                "num_chunks": 0,
                "chunks": []
            }
            
        # Prepare context
        context_parts = []
        for i, doc in enumerate(documents, 1):
            context_parts.append(f"[Log Chunk {i}]\n{doc.page_content}\n")
            
        context = "\n".join(context_parts)
        
        # Create prompt
        prompt = f"""You are an expert OpenShift/Kubernetes troubleshooter. Analyze the logs and answer the user's question.

User Question: {query}

Relevant Logs:
{context}

Instructions:
1. Analyze the logs carefully
2. Identify any errors, warnings, or issues
3. Provide a clear, actionable answer
4. If you see specific error codes or patterns, explain them
5. Suggest remediation steps if applicable

Answer:"""

        # Call LLM
        llama_client = LlamaStackClient(base_url=LLAMA_STACK_URL)
        response = llama_client.inference.chat_completion(
            model_id="llama-32-3b-instruct",
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False
        )
        
        # Extract answer
        answer = response.completion_message.content
        
        return {
            "answer": answer,
            "num_chunks": len(documents),
            "chunks": [doc.page_content[:500] + "..." for doc in documents]
        }
        
    except Exception as e:
        logger.error(f"Error answering question: {e}", exc_info=True)
        return {
            "answer": f"Error processing query: {str(e)}",
            "num_chunks": 0,
            "chunks": []
        }


# Sidebar - Configuration
with st.sidebar:
    st.title("🔧 Configuration")
    
    st.markdown("### 📍 Target Selection")
    
    # Namespace selection
    namespace_input = st.text_input(
        "Namespace",
        value=st.session_state.namespace,
        placeholder="e.g., test-problematic-pods"
    )
    
    # Pod selection
    pod_input = st.text_input(
        "Pod Name",
        value=st.session_state.pod_name,
        placeholder="e.g., crash-loop-app-..."
    )
    
    # Load logs button
    if st.button("📥 Load Logs & Create Retriever", type="primary"):
        if namespace_input and pod_input:
            st.session_state.namespace = namespace_input
            st.session_state.pod_name = pod_input
            
            success = load_logs_and_create_retriever(namespace_input, pod_input)
            if success:
                st.session_state.messages = []  # Clear chat history
                st.rerun()
        else:
            st.error("Please enter both namespace and pod name")
            
    st.markdown("---")
    
    # Status
    st.markdown("### 📊 Status")
    if st.session_state.retriever:
        st.success("✅ Retriever Active")
        st.metric("Namespace", st.session_state.namespace)
        st.metric("Pod", st.session_state.pod_name)
        if st.session_state.log_content:
            st.metric("Log Size", f"{len(st.session_state.log_content):,} chars")
    else:
        st.warning("⚠️ No retriever loaded")
        st.info("Enter namespace and pod name, then click 'Load Logs'")
        
    st.markdown("---")
    
    st.markdown("### 🎯 NVIDIA Approach")
    st.markdown("""
    - ✅ BM25 (keyword matching)
    - ✅ FAISS (semantic search)
    - ✅ RRF (rank fusion)
    - ✅ 20K chunks, 50% overlap
    - ✅ Granite embeddings
    - ✅ In-memory (ephemeral)
    """)

# Main area - Chat interface
st.title("🤖 AI Troubleshooter v8")
st.markdown("*NVIDIA-Style Hybrid Retrieval for OpenShift Logs*")

if not st.session_state.retriever:
    st.info("👈 Configure namespace and pod in the sidebar to get started")
else:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show metadata for assistant messages
            if message["role"] == "assistant" and "metadata" in message:
                with st.expander("📊 Retrieval Details"):
                    st.metric("Chunks Retrieved", message["metadata"]["num_chunks"])
                    if message["metadata"]["chunks"]:
                        st.markdown("**Top Chunks:**")
                        for i, chunk in enumerate(message["metadata"]["chunks"][:3], 1):
                            st.text_area(f"Chunk {i}", chunk, height=100, disabled=True)
    
    # Chat input
    if prompt := st.chat_input("Ask about the logs..."):
        # CRITICAL FIX: Augment query with selected namespace and pod
        # This ensures retrieval focuses on the correct pod
        augmented_query = f"{prompt} [Context: analyzing pod '{st.session_state.pod_name}' in namespace '{st.session_state.namespace}']"
        
        # Add user message (show original, not augmented)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Generate response with augmented query
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing logs..."):
                result = answer_question(augmented_query)
                
            st.markdown(result["answer"])
            
            # Show metadata
            if result["num_chunks"] > 0:
                with st.expander("📊 Retrieval Details"):
                    st.metric("Chunks Retrieved", result["num_chunks"])
                    if result["chunks"]:
                        st.markdown("**Top Chunks:**")
                        for i, chunk in enumerate(result["chunks"][:3], 1):
                            st.text_area(f"Chunk {i}", chunk, height=100, disabled=True)
                            
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "metadata": {
                "num_chunks": result["num_chunks"],
                "chunks": result["chunks"]
            }
        })

