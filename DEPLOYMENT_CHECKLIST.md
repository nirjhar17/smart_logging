# ✅ AI Troubleshooter v7 - Deployment Checklist

**Complete deployment verification checklist**

---

## Pre-Deployment Checklist

### 1. OpenShift Cluster Access
- [ ] Login to cluster: `oc login --token=... --server=https://api.loki123...`
- [ ] Verify current context: `oc whoami && oc cluster-info`
- [ ] Check cluster version: `oc version`

### 2. Dependencies Verification
- [ ] Llama Stack running: `oc get pods -n model | grep llamastack`
- [ ] LLM model available: `oc get pods -n model | grep llama-32-3b`
- [ ] Test Llama Stack API:
  ```bash
  curl http://llamastack-custom-distribution-service.model.svc.cluster.local:8321/v1/health
  ```

### 3. Local Files Ready
- [ ] All Python files present in `ai-troubleshooter-v7/`
- [ ] `v7-deployment.yaml` configured
- [ ] `v7-rbac.yaml` configured
- [ ] Documentation files created

---

## Deployment Steps

### Step 1: Create Namespace
```bash
oc create namespace ai-troubleshooter-v7
```
- [ ] Namespace created successfully
- [ ] Verify: `oc get namespace ai-troubleshooter-v7`

### Step 2: Deploy RBAC
```bash
oc apply -f v7-rbac.yaml
```
- [ ] ServiceAccount created: `ai-troubleshooter-v7-sa`
- [ ] ClusterRole created: `ai-troubleshooter-v7-reader`
- [ ] ClusterRoleBinding created: `ai-troubleshooter-v7-binding`
- [ ] Verify:
  ```bash
  oc get sa ai-troubleshooter-v7-sa -n ai-troubleshooter-v7
  oc get clusterrole ai-troubleshooter-v7-reader
  oc get clusterrolebinding ai-troubleshooter-v7-binding
  ```

### Step 3: Create ConfigMap
```bash
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v7"
oc create configmap ai-troubleshooter-v7-code \
  --from-file=app.py=v7_streamlit_app.py \
  --from-file=state_schema.py=v7_state_schema.py \
  --from-file=hybrid_retriever.py=v7_hybrid_retriever.py \
  --from-file=graph_nodes.py=v7_graph_nodes.py \
  --from-file=graph_edges.py=v7_graph_edges.py \
  --from-file=main_graph.py=v7_main_graph.py \
  --from-file=log_collector.py=v7_log_collector.py \
  -n ai-troubleshooter-v7
```
- [ ] ConfigMap created
- [ ] Verify: `oc describe configmap ai-troubleshooter-v7-code -n ai-troubleshooter-v7`
- [ ] Check all 7 files are present in ConfigMap

### Step 4: Deploy Application
```bash
oc apply -f v7-deployment.yaml -n ai-troubleshooter-v7
```
- [ ] Deployment created
- [ ] Service created
- [ ] Route created
- [ ] Verify:
  ```bash
  oc get deployment ai-troubleshooter-v7 -n ai-troubleshooter-v7
  oc get service ai-troubleshooter-v7-service -n ai-troubleshooter-v7
  oc get route ai-troubleshooter-v7 -n ai-troubleshooter-v7
  ```

### Step 5: Wait for Pod Ready
```bash
oc get pods -n ai-troubleshooter-v7 -w
```
- [ ] Pod in `ContainerCreating` state (0-30s)
- [ ] Pod in `Running` state (30s-120s)
- [ ] Pod shows `1/1 Ready` (120s-180s)
- [ ] Expected wait time: ~2-3 minutes

### Step 6: Check Pod Logs
```bash
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --tail=50
```
- [ ] See: "🚀 Starting AI Troubleshooter v7"
- [ ] See: "🎯 Starting AI Troubleshooter v7 (Multi-Agent) on port 8501"
- [ ] See: "You can now view your Streamlit app in your browser"
- [ ] No errors in logs

---

## Post-Deployment Verification

### 1. Network Connectivity
```bash
# Get route URL
ROUTE_URL=$(oc get route ai-troubleshooter-v7 -n ai-troubleshooter-v7 -o jsonpath='https://{.spec.host}')
echo $ROUTE_URL

# Test HTTP access
curl -I $ROUTE_URL
```
- [ ] HTTP/2 200 OK
- [ ] content-type: text/html
- [ ] Response time < 5s

### 2. RBAC Permissions
```bash
# Test namespace access
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- \
  oc get namespaces --no-headers | wc -l
```
- [ ] Returns 116 (or your cluster's namespace count)
- [ ] Not returning just "1" (which would indicate RBAC issue)

### 3. Llama Stack Connectivity
```bash
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- \
  curl -s http://llamastack-custom-distribution-service.model.svc.cluster.local:8321/v1/health
```
- [ ] Returns: `{"status":"healthy"}` or similar
- [ ] No connection errors

### 4. UI Access Test
- [ ] Open route URL in browser
- [ ] Streamlit UI loads without errors
- [ ] See: "AI OpenShift Troubleshooter v7 (Multi-Agent)"
- [ ] See: "Multi-Agent Workflow | Self-Correction | Hybrid Retrieval"
- [ ] Sidebar shows: "Multi-Agent Configuration"
- [ ] Namespace dropdown shows 116 namespaces (not just "default")

### 5. Functional Test
**Select a test pod:**
- Namespace: `test-problematic-pods` (or any with issues)
- Pod: Any pod (preferably one with logs)
- Options: ✅ Include Recent Logs, ✅ Include Pod Events
- Max Iterations: 3

**Click: 🚀 Start Multi-Agent Deep Analysis**

- [ ] Progress bar shows "📦 Collecting pod data..."
- [ ] Shows "Collected Data Summary" (Log Lines, Events, Pod Status)
- [ ] Progress bar shows "🤖 Starting multi-agent workflow..."
- [ ] Workflow executes (see console logs if enabled)
- [ ] Progress reaches 100%
- [ ] Status shows "✅ Multi-agent analysis complete!"

**Check Results:**
- [ ] Tab 1 shows "Multi-Agent Analysis" with recommendations
- [ ] Tab 2 shows "Evidence" with relevant log snippets
- [ ] Tab 3 shows "Workflow" execution trace
- [ ] Results include: ISSUE, REFERENCES, ACTIONS, FIX
- [ ] No error messages like "No relevant log data found"

---

## Health Monitoring

### Ongoing Health Checks

**Daily:**
```bash
# Pod status
oc get pods -n ai-troubleshooter-v7

# Route health
curl -I https://ai-troubleshooter-v7-ai-troubleshooter-v7.apps.rosa.loki123.orwi.p3.openshiftapps.com
```

**Weekly:**
```bash
# Check resource usage
oc adm top pod -n ai-troubleshooter-v7

# Check events
oc get events -n ai-troubleshooter-v7 --sort-by=.lastTimestamp | tail -20

# Review logs for errors
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --tail=100 | grep -i error
```

**Monthly:**
```bash
# Update dependencies (if needed)
# 1. Update v7-deployment.yaml pip install versions
# 2. Apply: oc apply -f v7-deployment.yaml -n ai-troubleshooter-v7
# 3. Restart: oc delete pod -l app=ai-troubleshooter-v7 -n ai-troubleshooter-v7
```

---

## Troubleshooting Common Issues

### Issue 1: Pod Not Starting

**Symptoms:**
- Pod stuck in `ContainerCreating`
- Pod in `CrashLoopBackOff`
- Pod in `ImagePullBackOff`

**Diagnosis:**
```bash
oc describe pod -n ai-troubleshooter-v7 -l app=ai-troubleshooter-v7
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 --previous
```

**Common Causes:**
- [ ] Image not accessible → Check image registry
- [ ] ConfigMap not found → Recreate ConfigMap
- [ ] Python dependency error → Check logs for pip install failures
- [ ] Port conflict → Verify 8501 not in use

---

### Issue 2: Only 1 Namespace Showing

**Symptoms:**
- UI dropdown shows only "default" namespace
- Should show 116 namespaces

**Diagnosis:**
```bash
# Check RBAC
oc get clusterrolebinding ai-troubleshooter-v7-binding

# Test permissions
oc auth can-i list namespaces --as=system:serviceaccount:ai-troubleshooter-v7:ai-troubleshooter-v7-sa
```

**Fix:**
- [ ] Ensure v7-rbac.yaml was applied
- [ ] Verify ClusterRoleBinding exists
- [ ] Restart pod: `oc delete pod -l app=ai-troubleshooter-v7 -n ai-troubleshooter-v7`

---

### Issue 3: Analysis Returns "No Relevant Data"

**Symptoms:**
- Workflow runs 3 iterations (max)
- Final result: "No relevant log data found"
- Console shows: "BM25 index not built yet"

**Diagnosis:**
```bash
oc logs -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 | grep "BM25"
```

**Fix:**
- [ ] Ensure latest code is in ConfigMap (with BM25 index building)
- [ ] Update ConfigMap if needed
- [ ] Restart pod
- [ ] Should see: "📊 Building BM25 index from... ✅ BM25 index built"

---

### Issue 4: Route Returns 503

**Symptoms:**
- `curl` returns HTTP 503
- Browser shows "Application is not available"

**Diagnosis:**
```bash
# Check pod status
oc get pods -n ai-troubleshooter-v7

# Check readiness probe
oc describe pod -n ai-troubleshooter-v7 -l app=ai-troubleshooter-v7 | grep -A5 "Readiness"
```

**Fix:**
- [ ] Wait for pod to be Ready (1/1)
- [ ] If pod not ready, check logs for errors
- [ ] Verify Streamlit started: look for "You can now view your Streamlit app"

---

### Issue 5: Llama Stack Errors

**Symptoms:**
- Analysis fails with "Failed to connect to Llama Stack"
- Logs show connection timeout

**Diagnosis:**
```bash
# Test from pod
oc exec -n ai-troubleshooter-v7 deployment/ai-troubleshooter-v7 -- \
  curl -v http://llamastack-custom-distribution-service.model.svc.cluster.local:8321/v1/health
```

**Fix:**
- [ ] Check Llama Stack is running: `oc get pods -n model | grep llamastack`
- [ ] Verify service exists: `oc get svc -n model | grep llamastack`
- [ ] Check network policy allows traffic between namespaces

---

## Performance Tuning

### For Heavy Load (Multiple Users)

**Scale horizontally:**
```bash
oc scale deployment ai-troubleshooter-v7 --replicas=3 -n ai-troubleshooter-v7
```

**Increase resources:**
```yaml
# In v7-deployment.yaml
resources:
  limits:
    cpu: "2"
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi
```

### For Faster Startup

**Pre-built image** (optional):
- Build custom image with dependencies pre-installed
- Update deployment to use custom image instead of dynamic installation

---

## Rollback Procedure

### If v7 has issues, rollback to v6:

```bash
# 1. Get v6 route
oc get route ai-troubleshooter-gui-v6 -n ai-troubleshooter-v6 -o jsonpath='https://{.spec.host}'

# 2. Optionally scale down v7
oc scale deployment ai-troubleshooter-v7 --replicas=0 -n ai-troubleshooter-v7

# 3. v6 is still running and accessible
```

### Full Uninstall (if needed):

```bash
# Delete all v7 resources
oc delete namespace ai-troubleshooter-v7

# Delete cluster-wide resources
oc delete clusterrole ai-troubleshooter-v7-reader
oc delete clusterrolebinding ai-troubleshooter-v7-binding
```

---

## Success Criteria Summary

✅ **Deployment Success:**
- Pod: 1/1 Running
- Route: HTTP 200
- Logs: No errors, Streamlit started
- RBAC: Can list all namespaces
- Llama Stack: Connectivity verified

✅ **Functional Success:**
- UI loads in browser
- 116 namespaces visible in dropdown
- Can select namespace and pod
- Analysis completes without errors
- Results show actionable recommendations
- BM25 index builds from logs
- Retrieved documents > 0

✅ **Quality Success:**
- Analysis relevant to pod issue
- Includes specific `oc` commands
- References actual log lines
- Provides clear fix steps
- Self-correction works (transforms query if needed)

---

**Last Updated**: October 12, 2025  
**Version**: 7.0.0  
**Cluster**: loki123.orwi.p3.openshiftapps.com  
**Status**: ✅ Deployed and Verified

