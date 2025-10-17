"""
AI Troubleshooter v7 - Log Collector
Collects logs from OpenShift and indexes them for retrieval
"""

import os
import subprocess
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from llama_stack_client import LlamaStackClient
from v7_hybrid_retriever import HybridRetriever


class OpenShiftLogCollector:
    """
    Collects logs from OpenShift using MCP or oc commands
    Indexes them into Milvus (via Llama Stack) + BM25
    """
    
    def __init__(
        self,
        llama_stack_url: str,
        vector_db_id: str = "openshift-logs-v7",
        namespaces: List[str] = None,
        use_mcp: bool = True
    ):
        """
        Initialize log collector
        
        Args:
            llama_stack_url: URL to Llama Stack service
            vector_db_id: Vector database ID
            namespaces: List of namespaces to collect from
            use_mcp: Use MCP functions (True) or oc commands (False)
        """
        self.llama_client = LlamaStackClient(base_url=llama_stack_url)
        self.vector_db_id = vector_db_id
        self.namespaces = namespaces or ["default"]
        self.use_mcp = use_mcp
        
        # Initialize hybrid retriever
        self.retriever = HybridRetriever(
            llama_stack_url=llama_stack_url,
            vector_db_id=vector_db_id
        )
        
        print(f"🔧 Log Collector initialized")
        print(f"   📊 Vector DB: {vector_db_id}")
        print(f"   📁 Namespaces: {namespaces}")
        print(f"   🔌 Data Source: {'MCP' if use_mcp else 'oc commands'}")
    
    def _detect_mcp_environment(self) -> bool:
        """Check if MCP functions are available"""
        try:
            # This would be replaced with actual MCP detection
            # For now, return False (will use oc commands)
            return False
        except:
            return False
    
    def collect_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        tail_lines: int = 100
    ) -> str:
        """
        Collect logs from a specific pod
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            tail_lines: Number of lines to retrieve
            
        Returns:
            Log content as string
        """
        try:
            if self.use_mcp:
                # Use MCP function (if available)
                # logs = mcp_kubernetes_pods_log(name=pod_name, namespace=namespace)
                # For now, fall back to oc
                pass
            
            # Fall back to oc command
            result = subprocess.run(
                ['oc', 'logs', pod_name, '-n', namespace, f'--tail={tail_lines}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"   ⚠️  Failed to get logs for {pod_name}: {result.stderr}")
                return ""
                
        except Exception as e:
            print(f"   ❌ Error collecting logs for {pod_name}: {e}")
            return ""
    
    def collect_pod_events(self, namespace: str, pod_name: str) -> str:
        """Collect events related to a pod"""
        try:
            result = subprocess.run(
                ['oc', 'get', 'events', '-n', namespace,
                 f'--field-selector=involvedObject.name={pod_name}',
                 '--sort-by=.lastTimestamp'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return ""
                
        except Exception as e:
            print(f"   ❌ Error collecting events: {e}")
            return ""
    
    def collect_namespace_logs(
        self,
        namespace: str,
        time_window_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Collect all logs from a namespace
        
        Args:
            namespace: Kubernetes namespace
            time_window_minutes: Only collect logs from last N minutes
            
        Returns:
            List of log documents
        """
        print(f"\n📦 Collecting logs from namespace: {namespace}")
        
        all_logs = []
        
        # Get list of pods
        try:
            result = subprocess.run(
                ['oc', 'get', 'pods', '-n', namespace, '-o', 'json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ❌ Failed to list pods in {namespace}")
                return all_logs
            
            pods_data = json.loads(result.stdout)
            pods = pods_data.get('items', [])
            
            print(f"   📊 Found {len(pods)} pods")
            
            # Collect logs from each pod
            for pod in pods:
                pod_name = pod['metadata']['name']
                pod_status = pod.get('status', {}).get('phase', 'Unknown')
                
                print(f"   🐳 Collecting from pod: {pod_name} ({pod_status})")
                
                # Get pod logs
                logs = self.collect_pod_logs(namespace, pod_name, tail_lines=100)
                
                # Get pod events
                events = self.collect_pod_events(namespace, pod_name)
                
                # Get pod status
                pod_status_info = pod.get('status', {})
                
                # Create log document
                if logs or events:
                    log_doc = {
                        'content': f"""
**Pod**: {pod_name}
**Namespace**: {namespace}
**Status**: {pod_status}

**Logs:**
{logs}

**Events:**
{events}

**Status Info:**
{json.dumps(pod_status_info, indent=2)}
""",
                        'metadata': {
                            'namespace': namespace,
                            'pod_name': pod_name,
                            'pod_status': pod_status,
                            'timestamp': datetime.now().isoformat(),
                            'log_type': 'pod_logs_and_events'
                        }
                    }
                    
                    all_logs.append(log_doc)
            
            print(f"   ✅ Collected {len(all_logs)} log documents")
            
        except Exception as e:
            print(f"   ❌ Error collecting namespace logs: {e}")
        
        return all_logs
    
    def collect_all_logs(self) -> List[Dict[str, Any]]:
        """Collect logs from all configured namespaces"""
        print(f"\n🔄 Collecting logs from {len(self.namespaces)} namespaces...")
        
        all_logs = []
        
        for namespace in self.namespaces:
            namespace_logs = self.collect_namespace_logs(namespace)
            all_logs.extend(namespace_logs)
        
        print(f"\n✅ Total collected: {len(all_logs)} log documents")
        
        return all_logs
    
    def ingest_to_vector_db(self, log_documents: List[Dict[str, Any]]):
        """
        Ingest log documents into Milvus via Llama Stack
        
        Args:
            log_documents: List of log documents to ingest
        """
        print(f"\n📊 Ingesting {len(log_documents)} documents into vector DB...")
        
        try:
            # Prepare RAG documents
            rag_docs = []
            for i, doc in enumerate(log_documents):
                rag_doc = RAGDocument(
                    document_id=f"log-{i}-{datetime.now().timestamp()}",
                    content=doc['content'],
                    metadata=doc.get('metadata', {})
                )
                rag_docs.append(rag_doc)
            
            # Ingest to Llama Stack
            self.llama_client.tool_runtime.rag_tool.insert(
                documents=rag_docs,
                vector_db_id=self.vector_db_id,
                chunk_size_in_tokens=512
            )
            
            print(f"✅ Successfully ingested to vector DB: {self.vector_db_id}")
            
        except Exception as e:
            print(f"❌ Failed to ingest to vector DB: {e}")
    
    def build_bm25_index(self, log_documents: List[Dict[str, Any]]):
        """
        Build BM25 index from log documents
        
        Args:
            log_documents: List of log documents
        """
        print(f"\n📊 Building BM25 index from {len(log_documents)} documents...")
        
        try:
            self.retriever.build_bm25_index(log_documents)
            print(f"✅ BM25 index built successfully")
        except Exception as e:
            print(f"❌ Failed to build BM25 index: {e}")
    
    def index_logs(self, log_documents: List[Dict[str, Any]]):
        """
        Index logs into both vector DB and BM25
        
        Args:
            log_documents: List of log documents
        """
        print(f"\n🔄 Indexing {len(log_documents)} log documents...")
        
        # Ingest to vector DB (Milvus)
        self.ingest_to_vector_db(log_documents)
        
        # Build BM25 index
        self.build_bm25_index(log_documents)
        
        print(f"\n✅ Indexing complete!")
    
    def run_collection_cycle(self):
        """Run a complete collection and indexing cycle"""
        print("\n" + "="*80)
        print("🔄 LOG COLLECTION CYCLE")
        print("="*80)
        
        # Collect logs
        logs = self.collect_all_logs()
        
        if not logs:
            print("⚠️  No logs collected")
            return
        
        # Index logs
        self.index_logs(logs)
        
        print("\n" + "="*80)
        print("✅ COLLECTION CYCLE COMPLETE")
        print("="*80)


def setup_log_collection_job(
    namespaces: List[str],
    interval_minutes: int = 15,
    llama_stack_url: str = None
):
    """
    Setup periodic log collection (to be run as a cron job)
    
    Args:
        namespaces: List of namespaces to collect from
        interval_minutes: Collection interval
        llama_stack_url: Llama Stack URL
    """
    import time
    
    if llama_stack_url is None:
        llama_stack_url = os.getenv(
            "LLAMA_STACK_URL",
            "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
        )
    
    collector = OpenShiftLogCollector(
        llama_stack_url=llama_stack_url,
        namespaces=namespaces
    )
    
    print(f"🔄 Starting log collection job (interval: {interval_minutes} min)")
    
    while True:
        try:
            collector.run_collection_cycle()
        except Exception as e:
            print(f"❌ Collection cycle error: {e}")
        
        print(f"\n⏳ Waiting {interval_minutes} minutes until next collection...")
        time.sleep(interval_minutes * 60)


# Example usage
if __name__ == "__main__":
    # Example: Collect logs from specific namespaces
    collector = OpenShiftLogCollector(
        llama_stack_url="http://llamastack-custom-distribution-service.model.svc.cluster.local:8321",
        namespaces=["ai-troubleshooter-v6", "model", "default"]
    )
    
    # Run one collection cycle
    collector.run_collection_cycle()

