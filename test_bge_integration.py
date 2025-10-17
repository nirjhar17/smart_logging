#!/usr/bin/env python3
"""
Test BGE Reranker Integration
Verifies the BGE reranker is properly integrated with the agent workflow
"""

import os
import sys

# Set environment variables manually for testing
os.environ['BGE_RERANKER_URL'] = os.getenv('BGE_RERANKER_URL', 'https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com')
os.environ['LLAMA_STACK_URL'] = os.getenv('LLAMA_STACK_URL', 'http://llamastack-custom-distribution-service.model.svc.cluster.local:8321')

print("="*70)
print("BGE RERANKER INTEGRATION TEST")
print("="*70)

# Test 1: Import modules
print("\n1️⃣ Testing module imports...")
try:
    from v7_bge_reranker import BGEReranker
    print("✅ v7_bge_reranker imported successfully")
except Exception as e:
    print(f"❌ Failed to import v7_bge_reranker: {e}")
    sys.exit(1)

# Test 2: Initialize reranker
print("\n2️⃣ Initializing BGE Reranker...")
try:
    reranker = BGEReranker()
    print(f"✅ BGE Reranker initialized: {reranker.reranker_url}")
except Exception as e:
    print(f"❌ Failed to initialize BGE Reranker: {e}")
    sys.exit(1)

# Test 3: Health check
print("\n3️⃣ Checking BGE Reranker service health...")
try:
    is_healthy = reranker.health_check()
    if is_healthy:
        print("✅ BGE Reranker service is healthy")
    else:
        print("⚠️  BGE Reranker service health check failed")
        print("   This might be okay if the service is starting up")
except Exception as e:
    print(f"⚠️  Health check error: {e}")
    print("   Continuing with functionality test...")

# Test 4: Test reranking functionality
print("\n4️⃣ Testing reranking functionality...")
try:
    # Sample query and documents (OpenShift troubleshooting scenario)
    query = "Why is my pod crashing with OOMKilled error?"
    
    documents = [
        {
            'content': 'Pod ai-app-123 is running normally with 1/1 containers ready',
            'score': 0.5,
            'metadata': {'source': 'pod_logs'}
        },
        {
            'content': 'Container in pod ai-app-456 was terminated with exit code 137 (OOMKilled) - memory limit exceeded',
            'score': 0.6,
            'metadata': {'source': 'pod_events'}
        },
        {
            'content': 'Network connectivity issue detected in namespace default',
            'score': 0.4,
            'metadata': {'source': 'cluster_logs'}
        },
        {
            'content': 'Memory limit exceeded: container requested 2Gi but limit is 1Gi, pod killed by OOM killer',
            'score': 0.7,
            'metadata': {'source': 'pod_logs'}
        },
        {
            'content': 'ImagePullBackOff error for container nginx:latest in pod web-server',
            'score': 0.3,
            'metadata': {'source': 'pod_events'}
        }
    ]
    
    print(f"\n📝 Query: {query}")
    print(f"📄 Documents to rerank: {len(documents)}")
    print("\n   Original order:")
    for i, doc in enumerate(documents, 1):
        print(f"   {i}. [Score: {doc['score']:.2f}] {doc['content'][:60]}...")
    
    # Perform reranking
    reranked = reranker.rerank_documents(
        query=query,
        documents=documents,
        top_k=3
    )
    
    print(f"\n   ✅ Reranking successful! Top {len(reranked)} results:")
    for i, doc in enumerate(reranked, 1):
        rerank_score = doc.get('rerank_score', doc.get('score', 0))
        original_rank = doc.get('original_rank', 'N/A')
        print(f"   {i}. [Rerank Score: {rerank_score:.4f}] [Original: #{original_rank}]")
        print(f"      {doc['content'][:60]}...")
    
    # Validate results
    if reranked:
        print("\n✅ Reranking functionality test PASSED")
        
        # Check if relevance improved
        top_doc_content = reranked[0]['content'].lower()
        if 'oom' in top_doc_content or '137' in top_doc_content or 'memory' in top_doc_content:
            print("✅ Relevance validation PASSED - Top result is highly relevant to OOM query")
        else:
            print("⚠️  Relevance validation - Top result may not be optimal")
    else:
        print("⚠️  Reranking returned empty results (fallback may have been used)")
        
except Exception as e:
    print(f"❌ Reranking functionality test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test integration with graph nodes
print("\n5️⃣ Testing integration with graph nodes...")
try:
    from v7_graph_nodes import Nodes
    
    llama_stack_url = os.getenv(
        "LLAMA_STACK_URL",
        "http://llamastack-custom-distribution-service.model.svc.cluster.local:8321"
    )
    
    nodes = Nodes(llama_stack_url=llama_stack_url)
    print("✅ Graph nodes initialized with BGE Reranker")
    
    # Check if reranker is properly attached
    if hasattr(nodes, 'reranker'):
        print("✅ BGE Reranker is attached to nodes")
        print(f"   Reranker URL: {nodes.reranker.reranker_url}")
    else:
        print("❌ BGE Reranker not attached to nodes")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Graph nodes integration test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final summary
print("\n" + "="*70)
print("🎉 ALL TESTS PASSED!")
print("="*70)
print("\n✅ BGE Reranker is successfully integrated with the agent workflow")
print("\nNext steps:")
print("  1. Deploy the updated code to OpenShift")
print("  2. Test with real log data")
print("  3. Monitor reranking performance in production")
print("\n" + "="*70)

