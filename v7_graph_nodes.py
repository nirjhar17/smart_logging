"""
AI Troubleshooter v7 - Graph Nodes
Implements each step of the multi-agent workflow
UPDATED: Agent 1 now uses NVIDIA-style hybrid retrieval (FAISS, no Milvus)
"""

import os
from typing import Dict, Any, List
from llama_stack_client import LlamaStackClient
from v7_state_schema import GraphState
from k8s_hybrid_retriever import K8sHybridRetriever  # NVIDIA-style retriever
from v7_bge_reranker import BGEReranker
import json


class Nodes:
    """
    Node implementations for the LangGraph workflow
    Each node is a specialized agent for a specific task
    """
    
    def __init__(
        self,
        llama_stack_url: str,
        llama_model: str = "llama-32-3b-instruct",
        vector_db_id: str = None,  # Not used in NVIDIA approach
        embedding_model: str = "granite-embedding-125m",
        reranker_url: str = None
    ):
        """Initialize nodes with Llama Stack client"""
        self.llama_client = LlamaStackClient(base_url=llama_stack_url)
        self.llama_model = llama_model
        self.llama_stack_url = llama_stack_url
        self.embedding_model = embedding_model
        
        # NVIDIA approach: No persistent retriever, build fresh each time
        # Retriever will be created per-query with fresh log data
        
        # Initialize BGE reranker
        self.reranker = BGEReranker(reranker_url=reranker_url)
        print(f"✅ Initialized BGE Reranker: {self.reranker.reranker_url}")
        print(f"✅ Using NVIDIA-style retrieval (FAISS, no Milvus)")
    
    def retrieve(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 1: NVIDIA-Style Hybrid Retrieval
        Builds fresh BM25 + FAISS indexes from current log context
        NO Milvus - all in-memory, ephemeral
        """
        print("\n" + "="*60)
        print("🔍 NODE 1: RETRIEVE (NVIDIA: BM25 + FAISS + RRF)")
        print("="*60)
        
        question = state["question"]
        log_context = state.get("log_context", "")
        pod_events = state.get("pod_events", "")
        
        # Combine logs and events
        combined_logs = log_context
        if pod_events:
            combined_logs = f"{log_context}\n\n=== Pod Events ===\n{pod_events}"
        
        if not combined_logs or len(combined_logs) < 50:
            print("⚠️  No log context provided, retrieval will be limited")
            return {
                "retrieved_docs": [],
                "question": question
            }
        
        print(f"📊 Log context size: {len(combined_logs)} chars")
        
        # NVIDIA APPROACH: Create fresh retriever with current logs
        # This builds BM25 + FAISS indexes automatically
        print("🏗️  Building NVIDIA-style retriever (BM25 + FAISS)...")
        try:
            retriever = K8sHybridRetriever(
                log_content=combined_logs,
                llama_stack_url=self.llama_stack_url
            )
            
            # Build enhanced query with context
            enhanced_query = self._build_enhanced_query(question, log_context, state)
            
            print(f"📝 Original Query: {question}")
            print(f"📝 Enhanced Query: {enhanced_query}")
            
            # Retrieve using NVIDIA's approach (EnsembleRetriever with RRF)
            # k=10 to ensure we get both Environment (secret) and Volumes (configmap) sections
            langchain_docs = retriever.retrieve(
                query=enhanced_query,
                k=10
            )
            
            # Convert LangChain Documents to our format
            retrieved_docs = []
            for i, doc in enumerate(langchain_docs):
                retrieved_docs.append({
                    'content': doc.page_content,
                    'score': 1.0 / (i + 1),  # Simple ranking score
                    'retrieval_method': 'nvidia_hybrid',
                    'metadata': doc.metadata if hasattr(doc, 'metadata') else {}
                })
            
            print(f"✅ Retrieved {len(retrieved_docs)} documents using NVIDIA approach")
            
            return {
                "retrieved_docs": retrieved_docs,
                "question": question
            }
            
        except Exception as e:
            print(f"❌ NVIDIA retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "retrieved_docs": [],
                "question": question
            }
    
    def rerank(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 2: Reranking
        Reranks retrieved documents using BGE Reranker v2-m3
        """
        print("\n" + "="*60)
        print("🎯 NODE 2: RERANK (BGE Reranker v2-m3)")
        print("="*60)
        
        question = state["question"]
        retrieved_docs = state["retrieved_docs"]
        
        if not retrieved_docs:
            print("⚠️  No documents to rerank")
            return {"reranked_docs": [], "question": question}
        
        try:
            print(f"📊 Reranking {len(retrieved_docs)} documents with BGE...")
            
            # Use BGE Reranker
            reranked_docs = self.reranker.rerank_documents(
                query=question,
                documents=retrieved_docs,
                top_k=10  # Keep all retrieved docs to ensure complete context
            )
            
            # Log reranking results
            print(f"\n✅ BGE Reranked to top {len(reranked_docs)} documents:")
            for i, doc in enumerate(reranked_docs, 1):
                print(f"  {i}. Score: {doc.get('rerank_score', 0):.4f} | "
                      f"Original Rank: {doc.get('original_rank', 'N/A')} → New Rank: {doc.get('new_rank', i)}")
                print(f"     {doc['content'][:100]}...")
            
            return {
                "reranked_docs": reranked_docs,
                "question": question
            }
            
        except Exception as e:
            print(f"❌ BGE Reranking error: {e}")
            print("⚠️  Falling back to score-based ranking")
            # Fallback: just take top 5 by score
            top_docs = sorted(
                retrieved_docs,
                key=lambda x: x.get('score', 0),
                reverse=True
            )[:5]
            return {"reranked_docs": top_docs, "question": question}
    
    def grade_documents(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 3: Grade Documents
        Scores each document for relevance to the question
        """
        print("\n" + "="*60)
        print("📊 NODE 3: GRADE DOCUMENTS")
        print("="*60)
        
        question = state["question"]
        reranked_docs = state["reranked_docs"]
        
        if not reranked_docs:
            print("⚠️  No documents to grade")
            return {
                "reranked_docs": [],
                "relevance_scores": [],
                "question": question
            }
        
        # Grade each document
        filtered_docs = []
        relevance_scores = []
        
        for i, doc in enumerate(reranked_docs):
            print(f"\n📄 Grading document {i+1}/{len(reranked_docs)}...")
            
            # Build grading prompt with NVIDIA's inclusive philosophy
            grading_prompt = f"""You are a document relevance evaluator for OpenShift troubleshooting.

CRITICAL INSTRUCTION:
⭐ Even PARTIAL relevance should be considered as 'yes' to avoid missing important context.
⭐ Configuration details (Secrets, ConfigMaps, Volumes, Environment) are RELEVANT even without explicit errors.

Question: {question}

Log Document:
{doc['content']}

EVALUATION CRITERIA:
- Contains error messages, warnings, failures → YES
- Contains resource references (Secrets, ConfigMaps, Volumes) → YES
- Contains pod status, conditions, or events → YES
- Contains environment variables or mounts → YES
- Only completely unrelated information → NO

Is this document relevant? Respond ONLY with 'yes' or 'no'.
"""
            
            try:
                # Use LLM for grading
                response = self.llama_client.inference.chat_completion(
                    model_id=self.llama_model,
                    messages=[
                        {"role": "user", "content": grading_prompt}
                    ],
                    sampling_params={
                        "strategy": {"type": "greedy"},
                        "max_tokens": 100
                    }
                )
                
                grade_text = response.completion_message.content.lower()
                
                # Parse response
                if 'yes' in grade_text:
                    print(f"   ✅ RELEVANT")
                    filtered_docs.append(doc)
                    relevance_scores.append(1.0)
                else:
                    print(f"   ❌ NOT RELEVANT")
                    relevance_scores.append(0.0)
                    
            except Exception as e:
                print(f"   ⚠️  Grading error: {e}, assuming relevant")
                filtered_docs.append(doc)
                relevance_scores.append(0.5)
        
        print(f"\n✅ Filtered to {len(filtered_docs)}/{len(reranked_docs)} relevant documents")
        
        return {
            "reranked_docs": filtered_docs,
            "relevance_scores": relevance_scores,
            "question": question
        }
    
    def generate(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 4: Generate Answer
        Generates final answer using LLM with context
        """
        print("\n" + "="*60)
        print("🤖 NODE 4: GENERATE ANSWER")
        print("="*60)
        
        question = state["question"]
        reranked_docs = state["reranked_docs"]
        namespace = state.get("namespace", "unknown")
        pod_name = state.get("pod_name", "")
        
        if not reranked_docs:
            generation = "❌ No relevant log data found to answer the question. Please try rephrasing or check if logs are available."
            return {"generation": generation, "question": question}
        
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(reranked_docs, 1):
            context_parts.append(f"**Log Snippet {i}** (Score: {doc.get('score', 0):.3f}):\n{doc['content']}\n")
        
        context = "\n".join(context_parts)
        
        # System prompt for OpenShift troubleshooting
        system_prompt = """You are a senior OpenShift SRE analyzing logs to troubleshoot issues.

⚠️ CRITICAL INSTRUCTION: The log evidence includes output from 'oc describe pod'. 
You MUST carefully read the ENTIRE pod describe output section by section:

1. **Pod Status/Conditions**: Check if pod is Running and Ready
   - If Status = "Running" and Ready = "True", the pod is HEALTHY
   - If Events section is empty or says "No resources found", there are NO ERRORS

2. **Environment Variables Section**: Check for missing Secrets
   - Look for patterns like: "Environment: DATABASE_URL: <set to the key 'X' in secret 'Y'>"
   - If you see "Optional: false" and the secret name, it's REQUIRED
   - Check if the pod is stuck in ContainerCreating - missing Secrets can prevent pod startup
   - List ALL missing Secrets separately from ConfigMap issues

3. **Volumes Section**: Check for missing ConfigMaps  
   - Look for: "Type: ConfigMap (a volume populated by a ConfigMap)"
   - If you see "Optional: false", the ConfigMap is REQUIRED
   - Check Events section for "configmap 'name' not found" messages
   - List ALL missing ConfigMaps separately from Secret issues

4. **Events Section**: Check for actual errors (MOST IMPORTANT!)
   - Look for: "FailedMount", "MountVolume.SetUp failed", "OOMKilled", "CrashLoopBackOff"
   - If Events section is EMPTY or shows NO errors, the pod is HEALTHY!

5. **Resource Limits/Requests**: Check for resource constraints
   - Look at CPU/Memory Limits and Requests in the container spec
   - Check if pod might be throttled or resource-constrained
   - If pod is CPU-intensive by design (e.g., named "cpu-intensive"), note this but don't call it an error

⚠️ VERY IMPORTANT: 
- DO NOT invent problems if the pod is Running, Ready, and has no error events!
- If pod is healthy, say: "✅ No issues detected. Pod is running normally."
- Only report actual errors that appear in the Events section or Container Status!

🎯 **FORMATTING REQUIREMENTS** (CRITICAL):
- You MUST put each section on a SEPARATE LINE
- Add a blank line between each section for readability
- Use the exact format shown below
- For commands, use proper markdown code blocks with ```bash syntax
- DO NOT mix different resource types in one command
- If multiple resources are missing, list EACH ONE separately

Provide your analysis in this EXACT format (each section on its own line):

🚨 **ISSUE**: [List ALL real issues found - if multiple resources missing, list each one]

📋 **ROOT CAUSE**: [Based on actual error evidence, explain why pod cannot start]

⚡ **IMMEDIATE ACTIONS**: [Only if real issues exist - list each action clearly]

🔧 **RESOLUTION**: [Only if real issues exist - use proper command formatting]

Example for missing resources:
🚨 **ISSUE**: Multiple missing resources:
- Missing ConfigMap: nonexistent-configmap
- Missing Secret: nonexistent-secret

📋 **ROOT CAUSE**: Pod stuck in ContainerCreating because:
1. Volume mount failing due to missing ConfigMap
2. Environment variable references missing Secret

⚡ **IMMEDIATE ACTIONS**:
1. Create the missing ConfigMap
2. Create the missing Secret

🔧 **RESOLUTION**:
Create the missing ConfigMap:
```bash
oc create configmap nonexistent-configmap --from-literal=config.yaml="sample content"
```

Create the missing Secret:
```bash
oc create secret generic nonexistent-secret --from-literal=database-url="postgresql://localhost:5432/db"
```

Maximum 300 words. BE HONEST if no issues exist! Use proper line breaks and code formatting!
"""
        
        # User prompt
        user_prompt = f"""Analyze this OpenShift issue:

**Namespace**: {namespace}
**Pod**: {pod_name or "All pods"}
**Question**: {question}

**Log Evidence**:
{context}

Provide your analysis in the format specified.
"""
        
        try:
            # Generate answer
            response = self.llama_client.inference.chat_completion(
                model_id=self.llama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                sampling_params={
                    "strategy": {"type": "greedy"},
                    "max_tokens": 500
                }
            )
            
            generation = response.completion_message.content
            
            # Add metadata
            generation += f"\n\n---\n**🎯 Analysis Metadata**:\n"
            generation += f"- **Model**: {self.llama_model}\n"
            generation += f"- **Evidence**: {len(reranked_docs)} log snippets\n"
            generation += f"- **Iteration**: {state.get('iteration', 0)}\n"
            
            print(f"✅ Generated answer ({len(generation)} chars)")
            
            return {"generation": generation, "question": question}
            
        except Exception as e:
            error_msg = f"❌ Generation error: {str(e)}"
            print(error_msg)
            return {"generation": error_msg, "question": question}
    
    def transform_query(self, state: GraphState) -> Dict[str, Any]:
        """
        NODE 5: Transform Query
        Rewrites the query for better retrieval (self-correction)
        """
        print("\n" + "="*60)
        print("🔄 NODE 5: TRANSFORM QUERY (Self-Correction)")
        print("="*60)
        
        original_question = state["question"]
        iteration = state.get("iteration", 0) + 1
        log_context = state.get("log_context", "")
        
        print(f"📝 Original Question: {original_question}")
        print(f"🔁 Iteration: {iteration}")
        
        # Build transformation prompt
        transform_prompt = f"""You are helping refine a log analysis query that didn't retrieve good results.

Original Question: {original_question}

Context: This is for OpenShift/Kubernetes log analysis.

Rewrite this question to be more specific and focused on log patterns, error codes, or component names.
Make it more likely to match actual log entries.

Return ONLY the rewritten question, nothing else.
"""
        
        try:
            response = self.llama_client.inference.chat_completion(
                model_id=self.llama_model,
                messages=[
                    {"role": "user", "content": transform_prompt}
                ],
                sampling_params={
                    "strategy": {"type": "greedy"},
                    "max_tokens": 100
                }
            )
            
            new_question = response.completion_message.content.strip()
            
            # Track transformation history
            transformation_history = state.get("transformation_history", [])
            transformation_history.append(original_question)
            
            print(f"📝 New Question: {new_question}")
            
            return {
                "question": new_question,
                "iteration": iteration,
                "transformation_history": transformation_history
            }
            
        except Exception as e:
            print(f"❌ Transformation error: {e}, keeping original question")
            return {
                "question": original_question,
                "iteration": iteration
            }
    
    def _build_enhanced_query(
        self,
        question: str,
        log_context: str,
        state: GraphState
    ) -> str:
        """
        Build enhanced query with additional context
        """
        enhanced_parts = [question]
        
        # Add pod name if available
        if state.get("pod_name"):
            enhanced_parts.append(f"pod:{state['pod_name']}")
        
        # Add namespace
        if state.get("namespace"):
            enhanced_parts.append(f"namespace:{state['namespace']}")
        
        # Extract key terms from log context (errors, statuses, resources)
        if log_context:
            # Look for common error patterns
            error_patterns = [
                'error', 'failed', 'crash', 'oom', 'timeout',
                'backoff', 'terminated', 'killed', 'unavailable'
            ]
            for pattern in error_patterns:
                if pattern in log_context.lower():
                    enhanced_parts.append(pattern)
                    break  # Only add one error pattern to avoid query bloat
            
            # Look for missing resource indicators
            resource_patterns = [
                ('secret', 'secret'),
                ('configmap', 'configmap'),
                ('environment:', 'environment'),
                ('volumes:', 'volume'),
                ('mountvolume', 'mount')
            ]
            for pattern, keyword in resource_patterns:
                if pattern in log_context.lower():
                    enhanced_parts.append(keyword)
        
        return " ".join(enhanced_parts)


# Singleton instance (will be initialized in main workflow)
_nodes_instance = None

def get_nodes_instance(llama_stack_url: str = None, vector_db_id: str = None, reranker_url: str = None) -> Nodes:
    """Get or create nodes instance"""
    global _nodes_instance
    if _nodes_instance is None:
        if llama_stack_url is None:
            llama_stack_url = os.getenv(
                "LLAMA_STACK_URL",
                "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
            )
        if vector_db_id is None:
            vector_db_id = os.getenv("VECTOR_DB_ID", "openshift-logs-v8")
        if reranker_url is None:
            reranker_url = os.getenv("BGE_RERANKER_URL", "https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com")
        _nodes_instance = Nodes(
            llama_stack_url=llama_stack_url,
            vector_db_id=vector_db_id,
            reranker_url=reranker_url
        )
    return _nodes_instance

