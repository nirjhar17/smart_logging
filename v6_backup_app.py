#!/usr/bin/env python3
"""
AI-Powered OpenShift Troubleshooter v6 - LLAMA STACK IMPLEMENTATION
Uses Llama Stack for RAG, embeddings, and AI agents
Features:
- Llama Stack RAG with OCP 4.16 documentation
- Granite embedding model (768 dimensions)
- OpenShift MCP server integration
- Llama 3.2 3B Instruct model
- Senior SRE-level technical analysis
"""

import streamlit as st
import subprocess
import json
import requests
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import os

# Llama Stack Integration
from llama_stack_client import LlamaStackClient, Agent
from llama_stack_client.types import RAGDocument

# Configuration - Llama Stack
LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321")
LLAMA_STACK_MODEL = os.getenv("LLAMA_STACK_MODEL", "llama-32-3b-instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "granite-embedding-125m")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
VECTOR_DB_ID = os.getenv("VECTOR_DB_ID", "ocp-4.16-support-docs")
OCP_MCP_URL = os.getenv("OCP_MCP_URL", "http://ocp-mcp-server.model.svc.cluster.local:8000/sse")

# Initialize Llama Stack Client
@st.cache_resource
def get_llama_stack_client():
    """Initialize and return Llama Stack client"""
    try:
        client = LlamaStackClient(base_url=LLAMA_STACK_URL)
        st.success(f"✅ Connected to Llama Stack at {LLAMA_STACK_URL}")
        return client
    except Exception as e:
        st.error(f"❌ Failed to connect to Llama Stack: {e}")
        return None

# Initialize client
llama_client = get_llama_stack_client()

# MCP Integration - Hybrid Data Collector (keep from original)
class KubernetesDataCollector:
    """
    Hybrid adapter that automatically detects environment and uses:
    - MCP tools when running in Cursor
    - oc commands when running in OpenShift production
    """
    
    def __init__(self):
        self.use_mcp = self._detect_mcp_environment()
        self.data_source = "MCP" if self.use_mcp else "oc commands"
        
    def _detect_mcp_environment(self):
        """Detect if MCP tools are available (Cursor environment)"""
        try:
            import builtins
            if hasattr(builtins, 'mcp_kubernetes_namespaces_list'):
                builtins.mcp_kubernetes_namespaces_list("test")
                return True
        except:
            try:
                mcp_kubernetes_namespaces_list("test")
                return True
            except NameError:
                pass
            except:
                return True
        return False
    
    def get_namespaces(self):
        """Get list of namespaces"""
        if self.use_mcp:
            try:
                result = mcp_kubernetes_namespaces_list("test")
                namespaces = []
                for line in result.split('\n'):
                    if line.strip() and 'Namespace' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            namespaces.append(parts[2])
                return namespaces[1:] if len(namespaces) > 1 else []
            except Exception as e:
                st.warning(f"MCP namespaces call failed: {e}, falling back to oc")
                return self._get_namespaces_oc()
        else:
            return self._get_namespaces_oc()
    
    def _get_namespaces_oc(self):
        """Fallback method using oc commands"""
        try:
            result = subprocess.run(['oc', 'get', 'namespaces', '--no-headers'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return [line.split()[0] for line in result.stdout.strip().split('\n') if line.strip()]
        except:
            pass
        return ["default"]
    
    def get_pods_in_namespace(self, namespace: str):
        """Get pods in a specific namespace"""
        if self.use_mcp:
            try:
                result = mcp_kubernetes_pods_list_in_namespace(namespace=namespace)
                pods = []
                for line in result.split('\n'):
                    if line.strip() and namespace in line and 'Pod' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            pods.append(parts[2])
                return pods
            except Exception as e:
                st.warning(f"MCP pods list failed: {e}, falling back to oc")
                return self._get_pods_oc(namespace)
        else:
            return self._get_pods_oc(namespace)
    
    def _get_pods_oc(self, namespace: str):
        """Fallback method using oc commands"""
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
    
    def get_pod_info(self, pod_name: str, namespace: str):
        """Get detailed pod information"""
        if self.use_mcp:
            try:
                return mcp_kubernetes_pods_get(name=pod_name, namespace=namespace)
            except Exception as e:
                st.warning(f"MCP pod get failed: {e}, falling back to oc")
                return self._get_pod_info_oc(pod_name, namespace)
        else:
            return self._get_pod_info_oc(pod_name, namespace)
    
    def _get_pod_info_oc(self, pod_name: str, namespace: str):
        """Fallback method using oc commands"""
        try:
            result = subprocess.run(['oc', 'get', 'pod', pod_name, '-n', namespace, '-o', 'json'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        return {}
    
    def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 50):
        """Get pod logs"""
        if self.use_mcp:
            try:
                return mcp_kubernetes_pods_log(name=pod_name, namespace=namespace)
            except Exception as e:
                st.warning(f"MCP pod logs failed: {e}, falling back to oc")
                return self._get_pod_logs_oc(pod_name, namespace, tail_lines)
        else:
            return self._get_pod_logs_oc(pod_name, namespace, tail_lines)
    
    def _get_pod_logs_oc(self, pod_name: str, namespace: str, tail_lines: int = 50):
        """Fallback method using oc commands"""
        try:
            result = subprocess.run(['oc', 'logs', pod_name, '-n', namespace, f'--tail={tail_lines}'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""
    
    def get_events(self, namespace: str):
        """Get events in namespace"""
        if self.use_mcp:
            try:
                return mcp_kubernetes_events_list(namespace=namespace)
            except Exception as e:
                st.warning(f"MCP events failed: {e}, falling back to oc")
                return self._get_events_oc(namespace)
        else:
            return self._get_events_oc(namespace)
    
    def _get_events_oc(self, namespace: str):
        """Fallback method using oc commands"""
        try:
            result = subprocess.run(['oc', 'get', 'events', '-n', namespace, '--sort-by=.lastTimestamp'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except:
            pass
        return ""

# Initialize the hybrid data collector
k8s_collector = KubernetesDataCollector()

# Llama Stack Setup Functions
def register_ocp_mcp_server():
    """Register OpenShift MCP server with Llama Stack"""
    if not llama_client:
        return False
    
    try:
        # Check if already registered
        toolgroups = llama_client.toolgroups.list()
        registered_ids = [tg.identifier for tg in toolgroups.data]
        
        if "mcp::openshift" in registered_ids:
            st.info("✅ OpenShift MCP server already registered")
            return True
        
        # Register new toolgroup
        llama_client.toolgroups.register(
            toolgroup_id="mcp::openshift",
            provider_id="model-context-protocol",
            mcp_endpoint={"uri": OCP_MCP_URL}
        )
        st.success("✅ Registered OpenShift MCP server with Llama Stack")
        return True
    except Exception as e:
        st.error(f"❌ Failed to register MCP server: {e}")
        return False

def setup_vector_database():
    """Setup vector database for OCP 4.16 documentation"""
    if not llama_client:
        return False
    
    try:
        # Check if vector DB already exists
        vector_dbs = llama_client.vector_dbs.list()
        existing_ids = [vdb.identifier for vdb in vector_dbs.data]
        
        if VECTOR_DB_ID in existing_ids:
            st.info(f"✅ Vector database '{VECTOR_DB_ID}' already exists")
            return True
        
        # Register new vector DB
        llama_client.vector_dbs.register(
            vector_db_id=VECTOR_DB_ID,
            embedding_model=EMBEDDING_MODEL,
            embedding_dimension=EMBEDDING_DIMENSION,
            provider_id="milvus"
        )
        st.success(f"✅ Created vector database: {VECTOR_DB_ID}")
        return True
    except Exception as e:
        st.error(f"❌ Failed to setup vector database: {e}")
        return False

def ingest_ocp_documentation():
    """Ingest OpenShift 4.16 documentation into vector database"""
    if not llama_client:
        return False
    
    try:
        # Check if documents are already ingested (this is a simplified check)
        # In production, you'd want a more robust way to track ingestion status
        
        documents = [
            RAGDocument(
                document_id="ocp-4.16-support",
                content="https://docs.redhat.com/en/documentation/openshift_container_platform/4.16/pdf/support/OpenShift_Container_Platform-4.16-Support-en-US.pdf",
                mime_type="application/pdf",
                metadata={"version": "4.16", "type": "support"}
            )
        ]
        
        with st.spinner("📄 Ingesting OpenShift 4.16 documentation (this may take a few minutes)..."):
            llama_client.tool_runtime.rag_tool.insert(
                documents=documents,
                vector_db_id=VECTOR_DB_ID,
                chunk_size_in_tokens=512
            )
        
        st.success("✅ Successfully ingested OpenShift 4.16 documentation")
        return True
    except Exception as e:
        # Check if error is about already existing documents
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            st.info("📄 Documentation already ingested")
            return True
        st.error(f"❌ Failed to ingest documentation: {e}")
        return False

def semantic_search_ocp_docs(query: str, issue_context: Dict, n_results: int = 5):
    """Perform semantic search using Llama Stack RAG tool"""
    if not llama_client:
        return []
    
    try:
        # Build enhanced query from context
        enhanced_query_parts = [f"Issue: {query}"]
        
        if issue_context.get('pod_status'):
            enhanced_query_parts.append(f"Pod Status: {issue_context['pod_status']}")
        if issue_context.get('container_state'):
            state = issue_context['container_state']
            enhanced_query_parts.append(f"Container State: {state}")
            # Add specific terms for better matching
            if "CrashLoopBackOff" in state:
                enhanced_query_parts.extend(["crash loop", "crashing", "restart loop", "pod crash"])
            elif "ImagePullBackOff" in state:
                enhanced_query_parts.extend(["image pull", "registry", "image not found"])
            elif "ContainerCreating" in state:
                enhanced_query_parts.extend(["container creation", "volume mount", "config mount"])
        
        if issue_context.get('restart_count', 0) > 0:
            restart_count = issue_context['restart_count']
            enhanced_query_parts.append(f"{restart_count} restarts")
            if restart_count > 3:
                enhanced_query_parts.extend(["high restart count", "frequent restarts"])
        
        enhanced_query = " | ".join(enhanced_query_parts)
        
        # Use Llama Stack RAG tool for knowledge search
        response = llama_client.tool_runtime.rag_tool.query(
            content=enhanced_query,
            vector_db_ids=[VECTOR_DB_ID],
            query_config={"max_chunks": n_results}
        )
        
        # Format results
        relevant_chunks = []
        for i, chunk in enumerate(response.chunks):
            relevant_chunks.append({
                'rank': i + 1,
                'content': chunk.content,
                'score': getattr(chunk, 'score', 0.0),
                'metadata': chunk.metadata if hasattr(chunk, 'metadata') else {}
            })
        
        return relevant_chunks
    except Exception as e:
        st.error(f"❌ Semantic search error: {e}")
        return []

def analyze_with_llama_stack_agent(pod_issue: str, pod_context: Dict, relevant_docs: List[Dict]) -> str:
    """Use Llama Stack Agent with RAG and MCP tools"""
    if not llama_client:
        return "❌ Llama Stack client not available"
    
    if not relevant_docs:
        return "❌ No relevant OpenShift documentation found for analysis"
    
    try:
        # Build context from RAG results
        docs_context = "\n\n".join([
            f"**Relevant Documentation Excerpt {i+1}** (Relevance: {doc.get('score', 0):.3f}):\n{doc['content']}"
            for i, doc in enumerate(relevant_docs[:3])  # Use top 3 docs
        ])
        
        # Admin-Focused System Prompt
        system_prompt = f"""You are a senior OpenShift SRE providing immediate, actionable troubleshooting guidance based on OpenShift 4.16 official documentation.

RELEVANT OPENSHIFT 4.16 DOCUMENTATION:
{docs_context}

RESPONSE FORMAT (STRICT):
```
🚨 **ISSUE**: [One-line summary]
📚 **DOCUMENTATION REFERENCE**: [Key finding from OCP 4.16 docs]
⚡ **ACTIONS**: [3-5 immediate oc commands to run]
🔧 **FIX**: [Specific resolution steps from documentation]
```

KEY REQUIREMENTS:
1. **Maximum 200 words total**
2. **Reference the provided OpenShift 4.16 documentation**
3. **Lead with immediate diagnostic commands**
4. **Use specific `oc` commands**
5. **Focus on "what to do NOW"**
6. **Cite documentation sections when relevant**

EXAMPLE GOOD RESPONSE:
```
🚨 **ISSUE**: Pod in CrashLoopBackOff with 16 restarts
📚 **DOCUMENTATION REFERENCE**: OCP 4.16 Support Guide Section 7.3 - Pod crash loops indicate application or configuration issues
⚡ **ACTIONS**: 
  oc logs <pod> --previous
  oc describe pod <pod>
  oc get events --field-selector involvedObject.name=<pod>
🔧 **FIX**: Check previous container logs for exit codes. Common causes: missing dependencies, configuration errors, or resource limits. Review pod resource requests/limits and application logs.
```

WHAT TO INCLUDE:
- ✅ Immediate diagnostic commands
- ✅ Specific fix instructions based on documentation
- ✅ Documentation references
- ✅ Concise, actionable format
"""
        
        # Create agent with RAG and MCP tools
        agent_config = {
            "model": LLAMA_STACK_MODEL,
            "instructions": system_prompt,
            "toolgroups": [
                {
                    "name": "builtin::rag",
                    "args": {"vector_db_ids": [VECTOR_DB_ID]}
                },
                "mcp::openshift"
            ],
            "tool_config": {"tool_choice": "auto"},
            "sampling_params": {
                "strategy": {"type": "greedy"},
                "max_tokens": 3500
            }
        }
        
        # Create agent
        agent_response = llama_client.agents.create(agent_config=agent_config)
        agent_id = agent_response.agent_id
        
        # Create session
        session_response = llama_client.agents.create_session(
            agent_id=agent_id,
            session_name=f"troubleshoot-{pod_context['pod']}"
        )
        session_id = session_response.session_id
        
        # Build user prompt
        user_prompt = f"""
Analyze this OpenShift pod issue and provide immediate actionable guidance based on OpenShift 4.16 documentation:

**Pod Issue**: {pod_issue}

**Technical Context**:
{json.dumps(pod_context, indent=2)}

Use the RAG tool to search OpenShift 4.16 documentation for relevant troubleshooting steps. Provide concise, admin-focused analysis.
"""
        
        # Create turn
        turn_response = llama_client.agents.create_turn(
            agent_id=agent_id,
            session_id=session_id,
            messages=[{"role": "user", "content": user_prompt}],
            stream=False
        )
        
        # Extract analysis from response
        analysis = ""
        for step in turn_response.steps:
            if hasattr(step, 'completion_message') and step.completion_message:
                analysis += step.completion_message.content
        
        # Add metadata
        analysis += f"""

---
**🎯 Llama Stack Analysis Enhanced with OCP 4.16 Documentation**
- **Model**: {LLAMA_STACK_MODEL}
- **Documentation**: OpenShift Container Platform 4.16 Support Guide
- **Relevant Chunks**: {len(relevant_docs)} documentation sections retrieved
- **Top Relevance**: {relevant_docs[0]['score']:.3f}
"""
        
        return analysis if analysis else "❌ No analysis generated"
    
    except Exception as e:
        return f"❌ Llama Stack Agent Analysis Error: {str(e)}"

def run_command(command: str) -> Tuple[str, str, int]:
    """Execute shell command and return output, error, and return code"""
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

# Page configuration
st.set_page_config(
    page_title="AI OpenShift Troubleshooter v6 (Llama Stack)",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        color: white !important;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 2rem;
        border: 1px solid #3b82f6;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.2);
    }
    
    .llama-badge {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.5rem 0;
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
    
    .doc-match {
        background: linear-gradient(90deg, #f59e0b, #f97316);
        color: white !important;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
        margin: 0.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎯 AI OpenShift Troubleshooter v6 (Llama Stack)</h1>
    <p>Llama Stack Intelligence: RAG + MCP + OpenShift 4.16 Documentation</p>
    <div class="llama-badge">
        🦙 Llama Stack + Granite Embeddings + OCP 4.16 Docs
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize Llama Stack components
if llama_client:
    with st.spinner("🔧 Initializing Llama Stack components..."):
        mcp_ready = register_ocp_mcp_server()
        vdb_ready = setup_vector_database()
        
        # Only try to ingest if user explicitly requests it via a button
        if 'docs_ingested' not in st.session_state:
            st.session_state.docs_ingested = False
    
    # Configuration status
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🦙 Llama Stack", "Connected" if llama_client else "Disconnected")
    with col2:
        st.metric("📊 Vector DB", VECTOR_DB_ID if vdb_ready else "Not Ready")
    with col3:
        st.metric("🔧 MCP Server", "Registered" if mcp_ready else "Not Ready")
    with col4:
        st.metric("📚 Model", LLAMA_STACK_MODEL)
else:
    st.error("❌ Llama Stack client not initialized. Check connection settings.")

# Sidebar for namespace and pod selection
st.sidebar.markdown("## 🔧 Llama Stack Analysis Configuration")

# Display data source status
data_source_color = "🟢" if k8s_collector.use_mcp else "🔵"
st.sidebar.info(f"{data_source_color} **Data Source**: {k8s_collector.data_source}")
st.sidebar.info(f"🦙 **AI Model**: {LLAMA_STACK_MODEL}")
st.sidebar.info(f"📚 **Documentation**: OpenShift 4.16")

if k8s_collector.use_mcp:
    st.sidebar.success("✨ MCP Integration Active")
else:
    st.sidebar.info("🔧 Using oc commands")

# Button to ingest documentation (one-time setup)
if llama_client and not st.session_state.docs_ingested:
    if st.sidebar.button("📄 Ingest OCP 4.16 Documentation", type="primary"):
        if ingest_ocp_documentation():
            st.session_state.docs_ingested = True
            st.rerun()

# Get available namespaces
namespaces = k8s_collector.get_namespaces()

selected_namespace = st.sidebar.selectbox(
    "📁 Select Namespace:",
    options=namespaces,
    index=namespaces.index("default") if "default" in namespaces else 0
)

# Get pods in selected namespace
if selected_namespace:
    pods = k8s_collector.get_pods_in_namespace(selected_namespace)
    
    selected_pod = st.sidebar.selectbox(
        "🐳 Select Pod:",
        options=pods if pods else ["No pods found"],
        disabled=not pods
    )

# Analysis configuration
st.sidebar.markdown("### 🎛️ Analysis Options")
include_logs = st.sidebar.checkbox("📝 Include Recent Logs", value=True)
include_events = st.sidebar.checkbox("📋 Include Pod Events", value=True)
max_docs = st.sidebar.selectbox("📚 Max Documentation Chunks", [3, 5, 7, 10], index=1)

# Main analysis section
if st.sidebar.button("🚀 Start Llama Stack Deep Analysis", type="primary"):
    if not selected_pod or selected_pod == "No pods found":
        st.error("❌ Please select a valid pod to analyze")
    elif not llama_client:
        st.error("❌ Llama Stack client not available")
    elif not st.session_state.docs_ingested:
        st.error("❌ Please ingest OCP 4.16 documentation first using the button in the sidebar")
    else:
        with st.spinner("🎯 Performing Llama Stack deep analysis..."):
            
            # Collect comprehensive data
            context_data = {
                "namespace": selected_namespace,
                "pod": selected_pod,
                "timestamp": datetime.now().isoformat()
            }
            
            # Get pod details
            pod_data = k8s_collector.get_pod_info(selected_pod, selected_namespace)
            if pod_data:
                context_data["pod_details"] = pod_data
                
                # Extract key information for semantic search
                status = pod_data.get('status', {})
                context_data["pod_status"] = status.get('phase', '')
                
                container_statuses = status.get('containerStatuses', [])
                for container in container_statuses:
                    state = container.get('state', {})
                    if 'waiting' in state:
                        context_data["container_state"] = state['waiting'].get('reason', '')
                    context_data["restart_count"] = container.get('restartCount', 0)
            
            # Get pod events if requested
            if include_events:
                events_output = k8s_collector.get_events(selected_namespace)
                context_data["events"] = events_output
            
            # Get recent logs if requested
            if include_logs:
                logs_output = k8s_collector.get_pod_logs(selected_pod, selected_namespace, tail_lines=50)
                context_data["recent_logs"] = logs_output
            
            # Build semantic search query
            search_query = f"Pod {selected_pod} in namespace {selected_namespace}"
            if context_data.get("container_state"):
                search_query += f" {context_data['container_state']}"
            if context_data.get("pod_status"):
                search_query += f" status {context_data['pod_status']}"
            
            # Perform semantic search
            st.info("🔍 Searching OpenShift 4.16 documentation...")
            relevant_docs = semantic_search_ocp_docs(search_query, context_data, n_results=max_docs)
            
            if not relevant_docs:
                st.error("❌ No relevant documentation found")
            else:
                # Perform Llama Stack analysis
                st.info("🤖 Analyzing with Llama Stack Agent...")
                ai_analysis = analyze_with_llama_stack_agent(search_query, context_data, relevant_docs)
                
                # Display results in tabs
                tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                    "🎯 Llama Stack Analysis",
                    "📚 Documentation Refs",
                    "📋 Pod Information",
                    "📋 Pod Events",
                    "📋 Pod Status",
                    "💾 Storage Check"
                ])
                
                with tab1:
                    st.markdown("### 🎯 Llama Stack Deep Analysis")
                    st.markdown('<div class="llama-badge">🦙 Llama Stack Agent + RAG + OCP 4.16 Documentation</div>', unsafe_allow_html=True)
                    
                    if ai_analysis.startswith("❌"):
                        st.error(ai_analysis)
                    else:
                        st.markdown(f'<div class="technical-analysis">{ai_analysis}</div>', unsafe_allow_html=True)
                
                with tab2:
                    st.markdown("### 📚 OpenShift 4.16 Documentation References")
                    st.markdown(f"**Found:** {len(relevant_docs)} relevant documentation sections")
                    
                    for doc in relevant_docs:
                        score = doc.get('score', 0)
                        if score >= 0.8:
                            score_class = "doc-match"
                            score_emoji = "🔥"
                        elif score >= 0.6:
                            score_class = "doc-match"
                            score_emoji = "✅"
                        else:
                            score_class = "doc-match"
                            score_emoji = "⚠️"
                        
                        st.markdown(f"""
                        <div class="technical-analysis">
                        <h5>📖 Documentation Excerpt {doc['rank']}</h5>
                        <div class="{score_class}">{score_emoji} Relevance: {score:.3f}</div>
                        <p><strong>Content:</strong></p>
                        <p>{doc['content'][:500]}...</p>
                        <p><strong>Metadata:</strong> {doc.get('metadata', {})}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                with tab3:
                    st.markdown("### 📋 Pod Information")
                    pod_describe_output, _, _ = run_command(f"oc describe pod {selected_pod} -n {selected_namespace}")
                    st.text(pod_describe_output)
                
                with tab4:
                    st.markdown("### 📋 Pod Events")
                    if include_events and "events" in context_data:
                        st.text(context_data["events"])
                    else:
                        events_output, _, _ = run_command(f"oc get events -n {selected_namespace} --field-selector involvedObject.name={selected_pod}")
                        st.text(events_output)
                
                with tab5:
                    st.markdown("### 📋 Pod Status")
                    if pod_data:
                        st.json(pod_data.get('status', {}))
                    else:
                        st.error("❌ Pod information not available")
                
                with tab6:
                    st.markdown("### 💾 Storage Check (PVC Issues)")
                    pvc_output, _, _ = run_command(f"oc get pvc -n {selected_namespace}")
                    st.text(pvc_output)

# Cluster Health Overview
st.markdown("---")
st.markdown("## 🏥 Cluster Health Overview")

col1, col2, col3 = st.columns(3)

with col1:
    nodes_output, _, _ = run_command("oc get nodes --no-headers")
    node_count = len([line for line in nodes_output.strip().split('\n') if line.strip()])
    ready_nodes = len([line for line in nodes_output.strip().split('\n') if 'Ready' in line])
    st.metric("Cluster Nodes", f"{ready_nodes}/{node_count} Ready")

with col2:
    all_pods = []
    for ns in namespaces[:10]:
        ns_pods = k8s_collector.get_pods_in_namespace(ns)
        all_pods.extend(ns_pods)
    
    total_pods = len(all_pods)
    st.metric("Total Pods", f"~{total_pods} (sampled)")

with col3:
    namespaces_output, _, _ = run_command("oc get namespaces --no-headers")
    namespace_count = len([line for line in namespaces_output.strip().split('\n') if line.strip()])
    st.metric("Namespaces", namespace_count)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🎯 AI OpenShift Troubleshooter v6 - Llama Stack | 
    Powered by Llama Stack + Granite Embeddings + OCP 4.16 Documentation</p>
</div>
""", unsafe_allow_html=True)
