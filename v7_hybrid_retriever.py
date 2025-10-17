"""
AI Troubleshooter v7 - Hybrid Retriever
Combines BM25 (lexical) + Milvus via Llama Stack (semantic)
"""

import os
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from llama_stack_client import LlamaStackClient
import re


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. BM25: Lexical/keyword matching (exact error codes, pod names)
    2. Milvus + Granite Embeddings: Semantic similarity
    
    Inspired by NVIDIA's approach but adapted for OpenShift + Llama Stack
    """
    
    def __init__(
        self,
        llama_stack_url: str,
        vector_db_id: str = "openshift-logs-v7",
        alpha: float = 0.5  # Weight: 0.5 = equal weight to BM25 and vector
    ):
        """
        Initialize hybrid retriever
        
        Args:
            llama_stack_url: URL to Llama Stack service
            vector_db_id: Vector database ID for logs
            alpha: Weight for combining scores (0-1)
                  0 = all BM25, 1 = all vector, 0.5 = equal
        """
        self.llama_client = LlamaStackClient(base_url=llama_stack_url)
        self.vector_db_id = vector_db_id
        self.alpha = alpha
        
        # BM25 index (built from logs)
        self.bm25_index = None
        self.bm25_corpus = []
        self.doc_metadata = []
        
    def build_bm25_index(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index from documents
        
        Args:
            documents: List of log documents with 'content' and 'metadata'
        """
        print(f"📊 Building BM25 index from {len(documents)} documents...")
        
        # Tokenize documents for BM25
        tokenized_corpus = []
        self.bm25_corpus = []
        self.doc_metadata = []
        
        for doc in documents:
            content = doc.get('content', '')
            self.bm25_corpus.append(content)
            self.doc_metadata.append(doc.get('metadata', {}))
            
            # Simple tokenization (can be improved)
            tokens = self._tokenize(content)
            tokenized_corpus.append(tokens)
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_corpus)
        print(f"✅ BM25 index built with {len(tokenized_corpus)} documents")
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for BM25
        Preserves important log patterns like error codes, IPs, etc.
        """
        # Lowercase and split on whitespace/punctuation
        # But preserve error codes like "HTTP 503", "ImagePullBackOff"
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def retrieve_bm25(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents using BM25 lexical matching
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            List of documents with BM25 scores
        """
        if self.bm25_index is None:
            print("⚠️  BM25 index not built yet")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        # Get BM25 scores
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:k]
        
        # Build results
        results = []
        for idx in top_indices:
            if bm25_scores[idx] > 0:  # Only include non-zero scores
                results.append({
                    'content': self.bm25_corpus[idx],
                    'score': float(bm25_scores[idx]),
                    'retrieval_method': 'bm25',
                    'metadata': self.doc_metadata[idx]
                })
        
        print(f"🔍 BM25 retrieved {len(results)} documents")
        return results
    
    def retrieve_vector(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve documents using Milvus vector search via Llama Stack
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            List of documents with similarity scores
        """
        try:
            # Use Llama Stack RAG tool for vector search
            response = self.llama_client.tool_runtime.rag_tool.query(
                content=query,
                vector_db_ids=[self.vector_db_id],
                query_config={"max_chunks": k}
            )
            
            # Format results
            results = []
            for i, chunk in enumerate(response.chunks):
                results.append({
                    'content': chunk.content,
                    'score': getattr(chunk, 'score', 0.0),
                    'retrieval_method': 'vector',
                    'metadata': chunk.metadata if hasattr(chunk, 'metadata') else {}
                })
            
            print(f"🔍 Vector search retrieved {len(results)} documents")
            return results
            
        except Exception as e:
            print(f"❌ Vector retrieval error: {e}")
            return []
    
    def hybrid_retrieve(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval combining BM25 and vector search
        Uses Reciprocal Rank Fusion (RRF) for score combination
        
        Args:
            query: Search query
            k: Number of documents to retrieve
            
        Returns:
            Combined ranked list of documents
        """
        print(f"\n🔄 Hybrid Retrieval for: '{query}'")
        
        # Retrieve from both sources
        bm25_results = self.retrieve_bm25(query, k=k*2)  # Get more for fusion
        vector_results = self.retrieve_vector(query, k=k*2)
        
        # Combine using Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            bm25_results,
            vector_results,
            k=k
        )
        
        print(f"✅ Hybrid retrieval returned {len(fused_results)} documents")
        return fused_results
    
    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        k: int = 10,
        rrf_k: int = 60  # RRF constant
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion: Combines rankings from multiple retrievers
        
        RRF Formula: score = Σ(1 / (k + rank))
        
        This is more robust than simple score averaging
        """
        # Build document lookup with RRF scores
        doc_scores = {}
        
        # Process BM25 results
        for rank, doc in enumerate(bm25_results, start=1):
            content = doc['content']
            rrf_score = 1.0 / (rrf_k + rank)
            
            if content not in doc_scores:
                doc_scores[content] = {
                    'content': content,
                    'rrf_score': 0.0,
                    'bm25_score': doc.get('score', 0.0),
                    'vector_score': 0.0,
                    'metadata': doc.get('metadata', {})
                }
            
            doc_scores[content]['rrf_score'] += rrf_score * (1 - self.alpha)
            doc_scores[content]['bm25_score'] = doc.get('score', 0.0)
        
        # Process vector results
        for rank, doc in enumerate(vector_results, start=1):
            content = doc['content']
            rrf_score = 1.0 / (rrf_k + rank)
            
            if content not in doc_scores:
                doc_scores[content] = {
                    'content': content,
                    'rrf_score': 0.0,
                    'bm25_score': 0.0,
                    'vector_score': doc.get('score', 0.0),
                    'metadata': doc.get('metadata', {})
                }
            
            doc_scores[content]['rrf_score'] += rrf_score * self.alpha
            doc_scores[content]['vector_score'] = doc.get('score', 0.0)
        
        # Sort by RRF score and return top-k
        sorted_docs = sorted(
            doc_scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )[:k]
        
        # Add retrieval method
        for doc in sorted_docs:
            doc['retrieval_method'] = 'hybrid'
            doc['score'] = doc['rrf_score']
        
        return sorted_docs


def test_hybrid_retriever():
    """Test function for hybrid retriever"""
    import os
    
    # Initialize
    llama_stack_url = os.getenv(
        "LLAMA_STACK_URL",
        "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
    )
    
    retriever = HybridRetriever(llama_stack_url)
    
    # Sample documents (would come from log collector)
    sample_docs = [
        {
            'content': 'Pod ai-troubleshooter-gui-v6-abc123 failed with ImagePullBackOff',
            'metadata': {'namespace': 'ai-troubleshooter-v6', 'type': 'error'}
        },
        {
            'content': 'Container exited with code 137 (OOMKilled)',
            'metadata': {'namespace': 'default', 'type': 'error'}
        },
        {
            'content': 'HTTP 503 Service Unavailable from llama-stack service',
            'metadata': {'namespace': 'model', 'type': 'error'}
        }
    ]
    
    # Build BM25 index
    retriever.build_bm25_index(sample_docs)
    
    # Test retrieval
    query = "pod failed to start"
    results = retriever.hybrid_retrieve(query, k=5)
    
    print("\n📊 Results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['content'][:100]}...")
        print(f"   Score: {result['score']:.4f} | Method: {result['retrieval_method']}")


if __name__ == "__main__":
    test_hybrid_retriever()

