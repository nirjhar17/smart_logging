#!/usr/bin/env python3
"""
Test script for NVIDIA-style hybrid retriever
"""

import sys
import logging
from k8s_log_fetcher import K8sLogFetcher
from k8s_hybrid_retriever import K8sHybridRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample log content for testing (without needing actual K8s cluster)
SAMPLE_LOGS = """
=== Pod: crash-loop-app-5466c959d4-dclps ===
2024-01-15 10:30:45 Starting application...
2024-01-15 10:30:46 Error: Failed to connect to database
2024-01-15 10:30:47 FATAL: Container terminated with exit code 137 (OOMKilled)
2024-01-15 10:30:47 Memory limit exceeded: container requested 2Gi but limit is 1Gi
2024-01-15 10:30:48 Pod terminated, attempting restart...

=== Pod: nginx-deployment-abc123 ===
2024-01-15 10:31:00 Nginx started successfully
2024-01-15 10:31:01 Listening on port 8080
2024-01-15 10:31:02 200 GET /health 0.002s
2024-01-15 10:31:05 200 GET /api/users 0.015s

=== Pod: image-pull-fail-xyz789 ===
2024-01-15 10:32:00 Attempting to pull image: myregistry/app:latest
2024-01-15 10:32:05 Error: Failed to pull image
2024-01-15 10:32:05 Error: unauthenticated pull rate limit exceeded
2024-01-15 10:32:05 ImagePullBackOff: Failed to pull container image
2024-01-15 10:32:10 Waiting for backoff period before retry...
"""


def test_hybrid_retriever():
    """Test the hybrid retriever with sample logs"""
    
    print("\n" + "="*80)
    print("🧪 TESTING NVIDIA-STYLE HYBRID RETRIEVER")
    print("="*80)
    
    # Configuration
    LLAMA_STACK_URL = "http://llama-stack-service.ai-troubleshooter-v8.svc.cluster.local:8321"
    
    print(f"\n📍 Configuration:")
    print(f"   Llama Stack URL: {LLAMA_STACK_URL}")
    print(f"   Log size: {len(SAMPLE_LOGS)} characters")
    
    # Test 1: Create hybrid retriever
    print("\n" + "-"*80)
    print("TEST 1: Creating Hybrid Retriever")
    print("-"*80)
    
    try:
        retriever = K8sHybridRetriever(
            log_content=SAMPLE_LOGS,
            llama_stack_url=LLAMA_STACK_URL
        )
        print("✅ Hybrid retriever created successfully!")
        
    except Exception as e:
        print(f"❌ Failed to create retriever: {e}")
        logger.error("Retriever creation failed", exc_info=True)
        return False
    
    # Test 2: Query about OOM errors
    print("\n" + "-"*80)
    print("TEST 2: Query - OOM Killed Errors")
    print("-"*80)
    
    query = "Why is my pod crashing with OOMKilled error?"
    print(f"Query: {query}")
    
    try:
        results = retriever.retrieve(query, k=3)
        print(f"\n✅ Retrieved {len(results)} results")
        
        for i, doc in enumerate(results, 1):
            print(f"\n📄 Result {i}:")
            print(f"   Content: {doc.page_content[:200]}...")
            print(f"   Metadata: {doc.metadata}")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.error("Query failed", exc_info=True)
        return False
    
    # Test 3: Query about image pull errors
    print("\n" + "-"*80)
    print("TEST 3: Query - Image Pull Errors")
    print("-"*80)
    
    query = "Why can't my pod pull the container image?"
    print(f"Query: {query}")
    
    try:
        results = retriever.retrieve(query, k=3)
        print(f"\n✅ Retrieved {len(results)} results")
        
        for i, doc in enumerate(results, 1):
            print(f"\n📄 Result {i}:")
            print(f"   Content: {doc.page_content[:200]}...")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.error("Query failed", exc_info=True)
        return False
    
    # Test 4: Query about healthy pods
    print("\n" + "-"*80)
    print("TEST 4: Query - Healthy Pods")
    print("-"*80)
    
    query = "Which pods are running normally?"
    print(f"Query: {query}")
    
    try:
        results = retriever.retrieve(query, k=3)
        print(f"\n✅ Retrieved {len(results)} results")
        
        for i, doc in enumerate(results, 1):
            print(f"\n📄 Result {i}:")
            print(f"   Content: {doc.page_content[:200]}...")
            
    except Exception as e:
        print(f"❌ Query failed: {e}")
        logger.error("Query failed", exc_info=True)
        return False
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80)
    
    return True


def test_log_fetcher():
    """Test the log fetcher (requires actual K8s access)"""
    
    print("\n" + "="*80)
    print("🧪 TESTING K8S LOG FETCHER")
    print("="*80)
    
    try:
        fetcher = K8sLogFetcher(use_oc=True)
        
        # Try to fetch from a test namespace
        print("\n📥 Attempting to fetch logs from test-problematic-pods...")
        logs = fetcher.fetch_logs_as_text(
            namespace="test-problematic-pods",
            tail=100
        )
        
        if logs:
            print(f"✅ Successfully fetched {len(logs)} characters")
            print(f"📄 Sample:\n{logs[:500]}...")
        else:
            print("⚠️  No logs fetched (namespace may not exist or no pods)")
            
    except Exception as e:
        print(f"❌ Log fetcher test failed: {e}")
        logger.error("Log fetcher failed", exc_info=True)
        return False
    
    return True


if __name__ == "__main__":
    print("\n🚀 Starting NVIDIA Approach Tests\n")
    
    # Test 1: Hybrid Retriever (works offline)
    success1 = test_hybrid_retriever()
    
    # Test 2: Log Fetcher (requires K8s access)
    print("\n" + "="*80)
    print("Note: Log fetcher test requires access to OpenShift cluster")
    print("="*80)
    
    response = input("\nTest log fetcher? (requires oc access) [y/N]: ")
    if response.lower() == 'y':
        success2 = test_log_fetcher()
    else:
        print("⏭️  Skipping log fetcher test")
        success2 = True
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"Hybrid Retriever: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"Log Fetcher: {'✅ PASS' if success2 else '⏭️  SKIP'}")
    print("="*80)
    
    sys.exit(0 if success1 and success2 else 1)


