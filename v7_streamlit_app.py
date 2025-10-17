#!/usr/bin/env python3
"""
AI Troubleshooter v7 - Multi-Agent Self-Corrective RAG
Integrates NVIDIA-inspired multi-agent workflow with v6 UI
"""

import streamlit as st
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import sys
import asyncio

# Add v7 modules to path
sys.path.insert(0, os.path.dirname(__file__))

# Import v7 multi-agent components
from main_graph import create_workflow, run_analysis
from state_schema import GraphState

# Import v6 KubernetesDataCollector (reuse!)
# We'll copy this from v6 since it's proven to work
from llama_stack_client import LlamaStackClient

# Configuration
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321")
LLAMA_STACK_MODEL = os.getenv("LLAMA_STACK_MODEL", "llama-32-3b-instruct")
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "openshift-logs-v7")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))

# KubernetesDataCollector from v6 (REUSED - proven to work)
class KubernetesDataCollector:
    """
    Hybrid adapter from v6 - REUSING AS-IS
    """
    
    def __init__(self):
        self.use_mcp = self._detect_mcp_environment()
        self.data_source = "MCP" if self.use_mcp else "oc commands"
        
    def _detect_mcp_environment(self):
        return False  # Use oc commands in production
    
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
                        pods.append(line.split()[0])
                return pods
        except:
            pass
        return []
    
    def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 50):
        try:
            result = subprocess.run(['oc', 'logs', pod_name, '-n', namespace, f'--tail={tail_lines}'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_events(self, namespace: str):
        try:
            result = subprocess.run(['oc', 'get', 'events', '-n', namespace, '--sort-by=.lastTimestamp'], 
                                  capture_output=True, text=True, timeout=30)
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

# Initialize components
k8s_collector = KubernetesDataCollector()

# Page configuration (same as v6)
st.set_page_config(
    page_title="AI Troubleshooter v7 (Multi-Agent)",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS (same as v6 with v7 branding)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6, #10b981);
        color: white !important;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #3b82f6;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
    }
    
    .multiagent-badge {
        background: linear-gradient(90deg, #10b981, #3b82f6, #8b5cf6);
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem 0;
    }
    
    .iteration-badge {
        background: linear-gradient(90deg, #f59e0b, #f97316);
        color: white !important;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem 0;
    }
    
    .technical-analysis {
        background-color: #f0f9ff !important;
        color: #0c4a6e !important;
        border-left: 6px solid #3b82f6;
        border: 1px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Header (v7 branding)
st.markdown("""
<div class="main-header">
    <h1>🎯 AI Troubleshooter v7 (Multi-Agent)</h1>
    <p>Self-Corrective RAG: BM25 + Vector + Reranking + Grading + Query Transformation</p>
    <div class="multiagent-badge">
        🤖 Multi-Agent Workflow | 🔄 Self-Correction | 📊 Hybrid Retrieval
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar configuration (reusing v6 structure)
st.sidebar.markdown("## 🔧 Multi-Agent Configuration")

# Display data source
data_source_color = "🟢" if k8s_collector.use_mcp else "🔵"
st.sidebar.info(f"{data_source_color} **Data Source**: {k8s_collector.data_source}")
st.sidebar.info(f"🤖 **AI Model**: {LLAMA_STACK_MODEL}")
st.sidebar.info(f"🔄 **Max Iterations**: {MAX_ITERATIONS}")

# Get namespaces
namespaces = k8s_collector.get_namespaces()

selected_namespace = st.sidebar.selectbox(
    "📁 Select Namespace:",
    options=namespaces,
    index=namespaces.index("default") if "default" in namespaces else 0
)

# Get pods
if selected_namespace:
    pods = k8s_collector.get_pods_in_namespace(selected_namespace)
    
    selected_pod = st.sidebar.selectbox(
        "🐳 Select Pod:",
        options=pods if pods else ["No pods found"],
        disabled=not pods
    )

# Analysis options
st.sidebar.markdown("### 🎛️ Analysis Options")
include_logs = st.sidebar.checkbox("📝 Include Recent Logs", value=True)
include_events = st.sidebar.checkbox("📋 Include Pod Events", value=True)
max_iterations = st.sidebar.slider("🔄 Max Self-Correction Iterations", 1, 5, MAX_ITERATIONS)

# Metrics display
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🤖 Agent Type", "Multi-Agent")
with col2:
    st.metric("🔍 Retrieval", "Hybrid")
with col3:
    st.metric("🎯 Reranking", "Enabled")
with col4:
    st.metric("📊 Grading", "Enabled")

# Main analysis button
if st.sidebar.button("🚀 Start Multi-Agent Deep Analysis", type="primary"):
    if not selected_pod or selected_pod == "No pods found":
        st.error("❌ Please select a valid pod to analyze")
    else:
        # Progress container
        progress_container = st.container()
        
        with progress_container:
            st.markdown("### 🔄 Multi-Agent Workflow Progress")
            
            # Create progress placeholders
            status_placeholder = st.empty()
            iteration_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            status_placeholder.info("🔄 Initializing multi-agent workflow...")
            
            # Collect pod data
            status_placeholder.info("📦 Collecting pod data...")
            progress_bar.progress(10)
            
            pod_info = k8s_collector.get_pod_info(selected_pod, selected_namespace)
            
            # Get logs if requested
            logs = ""
            if include_logs:
                status_placeholder.info("📝 Collecting pod logs...")
                progress_bar.progress(20)
                logs = k8s_collector.get_pod_logs(selected_pod, selected_namespace, tail_lines=100)
            
            # Get events if requested
            events = ""
            if include_events:
                status_placeholder.info("📋 Collecting pod events...")
                progress_bar.progress(30)
                events = k8s_collector.get_events(selected_namespace)
            
            # Build question
            pod_status = pod_info.get('status', {})
            phase = pod_status.get('phase', 'Unknown')
            
            # Auto-generate question based on pod status
            if phase != 'Running':
                question = f"Why is pod {selected_pod} in {phase} state?"
            else:
                question = f"Analyze pod {selected_pod} for any issues or errors"
            
            # Show collected data summary
            st.markdown("#### 📊 Collected Data Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Log Lines", len(logs.split('\n')) if logs else 0)
            with col2:
                st.metric("Events", len(events.split('\n')) if events else 0)
            with col3:
                st.metric("Pod Status", phase)
            
            # Run multi-agent analysis
            status_placeholder.info("🤖 Starting multi-agent workflow...")
            progress_bar.progress(40)
            
            try:
                # Run v7 multi-agent analysis
                result = run_analysis(
                    question=question,
                    namespace=selected_namespace,
                    pod_name=selected_pod,
                    log_context=logs,
                    pod_events=events,
                    pod_status=pod_status,
                    time_window=30,
                    max_iterations=max_iterations,
                    llama_stack_url=LLAMA_STACK_URL
                )
                
                progress_bar.progress(100)
                status_placeholder.success("✅ Multi-agent analysis complete!")
                
                # Display results
                if result.get("success"):
                    st.markdown("---")
                    st.markdown("## 📊 Multi-Agent Analysis Results")
                    
                    # Show iteration info
                    iterations = result.get('iterations', 0)
                    if iterations > 0:
                        st.markdown(f'<div class="iteration-badge">🔄 Self-Corrected: {iterations} iterations</div>', unsafe_allow_html=True)
                    
                    # Create tabs for results
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "🎯 Analysis",
                        "📚 Evidence",
                        "🔄 Workflow",
                        "📋 Pod Details",
                        "📊 Metrics"
                    ])
                    
                    with tab1:
                        st.markdown("### 🎯 Multi-Agent Analysis")
                        st.markdown('<div class="technical-analysis">', unsafe_allow_html=True)
                        st.markdown(result['answer'])
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with tab2:
                        st.markdown("### 📚 Evidence Used")
                        docs = result.get('relevant_docs', [])
                        st.write(f"**Found {len(docs)} relevant log snippets**")
                        
                        for i, doc in enumerate(docs, 1):
                            with st.expander(f"📄 Evidence {i} (Score: {doc.get('score', 0):.3f})"):
                                st.code(doc.get('content', '')[:500])
                                st.json(doc.get('metadata', {}))
                    
                    with tab3:
                        st.markdown("### 🔄 Workflow Execution")
                        st.write(f"**Original Question:** {result['original_question']}")
                        
                        if result.get('transformation_history'):
                            st.write("**Query Transformations:**")
                            for i, query in enumerate(result['transformation_history'], 1):
                                st.write(f"{i}. {query}")
                        
                        st.write(f"**Final Question:** {result['question']}")
                        
                        # Workflow diagram
                        st.markdown("**Workflow Steps:**")
                        st.markdown("""
                        1. 🔍 **Hybrid Retrieval** (BM25 + Vector)
                        2. 🎯 **Reranking** (Score sorting)
                        3. 📊 **Grading** (Relevance check)
                        4. 🤖 **Generation** (LLM answer)
                        5. 🔄 **Self-Correction** (If needed)
                        """)
                    
                    with tab4:
                        st.markdown("### 📋 Pod Information")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Pod Status:**")
                            st.json(pod_status)
                        
                        with col2:
                            st.write("**Metadata:**")
                            st.json(result['metadata'])
                        
                        if logs:
                            with st.expander("📝 Raw Logs"):
                                st.code(logs)
                        
                        if events:
                            with st.expander("📋 Raw Events"):
                                st.code(events)
                    
                    with tab5:
                        st.markdown("### 📊 Analysis Metrics")
                        
                        metrics = result['metadata']
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Iterations", result['iterations'])
                        with col2:
                            st.metric("Docs Retrieved", metrics['num_docs_retrieved'])
                        with col3:
                            st.metric("Docs Relevant", metrics['num_docs_relevant'])
                        with col4:
                            st.metric("Avg Relevance", f"{metrics['avg_relevance']:.2f}")
                        
                        st.markdown("**Performance:**")
                        st.write(f"- Multi-agent workflow completed in {result['iterations']} iterations")
                        st.write(f"- Retrieved {metrics['num_docs_retrieved']} documents")
                        st.write(f"- Filtered to {metrics['num_docs_relevant']} relevant documents")
                        st.write(f"- Average relevance score: {metrics['avg_relevance']:.2%}")
                
                else:
                    st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                progress_bar.progress(100)
                status_placeholder.error("❌ Analysis failed")
                st.error(f"❌ Error during analysis: {str(e)}")
                import traceback
                with st.expander("🐛 Error Details"):
                    st.code(traceback.format_exc())

# Cluster Health Overview (reusing v6 structure)
st.markdown("---")
st.markdown("## 🏥 Cluster Health Overview")

col1, col2, col3 = st.columns(3)

with col1:
    try:
        result = subprocess.run(['oc', 'get', 'nodes', '--no-headers'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            nodes = result.stdout.strip().split('\n')
            ready_nodes = len([n for n in nodes if 'Ready' in n])
            st.metric("Cluster Nodes", f"{ready_nodes}/{len(nodes)} Ready")
    except:
        st.metric("Cluster Nodes", "N/A")

with col2:
    total_pods = sum([len(k8s_collector.get_pods_in_namespace(ns)) for ns in namespaces[:5]])
    st.metric("Total Pods", f"~{total_pods} (sampled)")

with col3:
    st.metric("Namespaces", len(namespaces))

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🎯 AI Troubleshooter v7 - Multi-Agent Self-Corrective RAG | 
    Inspired by NVIDIA's Log Analysis Architecture | 
    Powered by Llama Stack + LangGraph</p>
</div>
""", unsafe_allow_html=True)
