"""
Simulate why BM25/FAISS might miss the secret issue
"""

# Simulated describe output (what's in the logs)
describe_output = """
Environment:
  DATABASE_URL: <set to the key 'database-url' in secret 'nonexistent-secret'>

Volumes:
  app-config:
    Type: ConfigMap
    Name: nonexistent-configmap

Events:
  Warning FailedMount (x8945 over 12d) kubelet
    MountVolume.SetUp failed for volume "app-config" : 
    configmap "nonexistent-configmap" not found
"""

# User's likely query
user_query = "Why is my pod failing?"

# BM25 Analysis: Count keyword matches
print("=" * 60)
print("BM25 KEYWORD ANALYSIS")
print("=" * 60)

query_tokens = user_query.lower().split()
print(f"Query tokens: {query_tokens}")
print()

sections = {
    "Environment (secret)": "DATABASE_URL secret nonexistent-secret",
    "Volumes (configmap)": "ConfigMap nonexistent-configmap",
    "Events (error)": "Warning FailedMount x8945 kubelet failed configmap nonexistent-configmap not found"
}

for section, text in sections.items():
    text_lower = text.lower()
    matches = sum(1 for token in query_tokens if token in text_lower)
    print(f"{section:30} → {matches} keyword matches")
    print(f"  Text: {text[:60]}...")
    print()

print("\n" + "=" * 60)
print("THE PROBLEM")
print("=" * 60)
print("Query: 'Why is my pod failing?'")
print("  - 'failing' → matches 'failed' in Events ✓")
print("  - 'pod' → not in any section ✗")
print()
print("Events section has:")
print("  - 'failed' keyword (query match!)")
print("  - 'x8945' (high frequency!)")
print("  - Error message (semantic importance!)")
print()
print("Environment section has:")
print("  - NO 'failed' keyword ✗")
print("  - NO 'error' keyword ✗")
print("  - Just config info (low semantic importance)")
print()
print("Result: Events section ranks MUCH HIGHER than Environment!")
print()
print("=" * 60)
print("SOLUTION")
print("=" * 60)
print("Need to ensure BOTH sections are retrieved:")
print("1. Retrieve more chunks (k=10 instead of k=5)")
print("2. Use better query: 'What resources are missing for this pod?'")
print("3. Force retrieval of pod spec sections (Environment, Volumes)")
print("4. Use structured parsing, not just semantic search")
