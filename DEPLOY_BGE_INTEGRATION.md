# Deploy BGE Reranker Integration

## Quick Start

Follow these steps to deploy the BGE reranker integration to your OpenShift cluster.

## Prerequisites

✅ BGE Reranker InferenceService is deployed in `model` namespace
✅ Service is accessible at: `https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com`
✅ You have `oc` CLI configured and logged in
✅ Target namespace: `ai-troubleshooter-v8`

## Deployment Steps

### Step 1: Verify BGE Reranker Service

```bash
# Check if BGE reranker is running
oc get isvc bge-reranker -n model

# Expected output:
# NAME           URL                                                              READY   PREV   LATEST
# bge-reranker   https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com   True

# Check the predictor pod
oc get pods -n model -l serving.kserve.io/inferenceservice=bge-reranker

# Test the service
curl -X POST https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com/score \
  -H "Content-Type: application/json" \
  -d '{
    "model": "bge-reranker",
    "text": "test query",
    "text_pair": ["test document 1", "test document 2"]
  }'
```

### Step 2: Update ConfigMap

The ConfigMap needs to include the new BGE reranker module:

```bash
# Navigate to the project directory
cd "/Users/njajodia/Cursor Experiments/logs_monitoring/ai-troubleshooter-v8"

# Backup existing configmap
oc get configmap ai-troubleshooter-v7-code -n ai-troubleshooter-v8 -o yaml > backup-configmap.yaml

# Create updated configmap with BGE reranker
oc create configmap ai-troubleshooter-v8-code \
  --from-file=app.py=v7_streamlit_app.py \
  --from-file=v7_main_graph.py \
  --from-file=v7_graph_nodes.py \
  --from-file=v7_graph_edges.py \
  --from-file=v7_state_schema.py \
  --from-file=v7_hybrid_retriever.py \
  --from-file=v7_bge_reranker.py \
  --from-file=v7_log_collector.py \
  -n ai-troubleshooter-v8 \
  --dry-run=client -o yaml | oc apply -f -
```

### Step 3: Update Deployment

Update the deployment with the new environment variable:

```bash
# Apply the updated deployment
oc apply -f v7-deployment.yaml -n ai-troubleshooter-v8

# Or manually patch the existing deployment
oc set env deployment/ai-troubleshooter-v8 \
  BGE_RERANKER_URL="https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com" \
  -n ai-troubleshooter-v8
```

### Step 4: Restart the Application

```bash
# Rollout restart to pick up new configmap and environment
oc rollout restart deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8

# Watch the rollout status
oc rollout status deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8

# Check pod logs
oc logs -f deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8
```

### Step 5: Verify Integration

```bash
# Check if pod is running
oc get pods -n ai-troubleshooter-v8 -l app=ai-troubleshooter-v8

# View logs to confirm BGE reranker is initialized
oc logs -n ai-troubleshooter-v8 -l app=ai-troubleshooter-v8 | grep -i "BGE\|reranker"

# Expected log output:
# ✅ Initialized BGE Reranker: https://bge-reranker-model.apps.rosa...
```

### Step 6: Test via UI

1. Access the application:
   ```bash
   oc get route ai-troubleshooter-v8 -n ai-troubleshooter-v8 -o jsonpath='{.spec.host}'
   ```

2. Open the URL in your browser

3. Run a test query:
   - Select a namespace
   - Select a pod (or "All Pods")
   - Enter query: "Why is my pod failing with OOMKilled?"
   - Click "🚀 Analyze with AI"

4. Check the output:
   - Look for "🎯 NODE 2: RERANK (BGE Reranker v2-m3)" in the workflow
   - Verify reranking scores are displayed

## Verification Checklist

- [ ] BGE reranker service is running in `model` namespace
- [ ] ConfigMap includes `v7_bge_reranker.py`
- [ ] Deployment has `BGE_RERANKER_URL` environment variable
- [ ] Application pod is running
- [ ] Logs show BGE reranker initialization
- [ ] Test query returns reranked results
- [ ] No errors in application logs

## Troubleshooting

### Issue: BGE Reranker Not Found

**Symptom**: Error "Cannot connect to reranker service"

**Solution**:
```bash
# Check if service is accessible
oc run test-curl --image=curlimages/curl --rm -it --restart=Never -- \
  curl -X POST https://bge-reranker-model.apps.rosa.loki123.orwi.p3.openshiftapps.com/health
```

### Issue: Import Error

**Symptom**: "ModuleNotFoundError: No module named 'v7_bge_reranker'"

**Solution**:
```bash
# Verify configmap has the file
oc get configmap ai-troubleshooter-v8-code -n ai-troubleshooter-v8 -o yaml | grep "v7_bge_reranker.py"

# If missing, recreate configmap (see Step 2)
```

### Issue: Fallback Ranking Used

**Symptom**: Logs show "Using fallback ranking (original order)"

**Solution**:
- Check BGE reranker service logs:
  ```bash
  oc logs -n model -l serving.kserve.io/inferenceservice=bge-reranker
  ```
- Verify service URL is correct in environment
- Test service directly with curl

## Rollback Procedure

If integration fails, rollback to previous version:

```bash
# Restore previous configmap
oc apply -f backup-configmap.yaml -n ai-troubleshooter-v8

# Remove BGE_RERANKER_URL environment variable
oc set env deployment/ai-troubleshooter-v8 BGE_RERANKER_URL- -n ai-troubleshooter-v8

# Restart
oc rollout restart deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8
```

## Performance Monitoring

After deployment, monitor these metrics:

```bash
# Watch pod resource usage
oc adm top pod -n ai-troubleshooter-v8 -l app=ai-troubleshooter-v8

# Watch BGE reranker usage
oc adm top pod -n model -l serving.kserve.io/inferenceservice=bge-reranker

# Check application logs for reranking latency
oc logs -n ai-troubleshooter-v8 -l app=ai-troubleshooter-v8 | grep "Reranking\|Score:"
```

## Next Steps

1. **Fine-tune Performance**: Adjust `top_k` parameter in reranker calls
2. **Monitor Metrics**: Track reranking success rate and latency
3. **A/B Testing**: Compare with/without reranking for quality assessment
4. **Scale**: Increase BGE reranker replicas if needed

## Support

For issues:
1. Check application logs: `oc logs -f deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8`
2. Check BGE reranker logs: `oc logs -n model -l serving.kserve.io/inferenceservice=bge-reranker`
3. Run integration test: `python test_bge_integration.py`
4. Review documentation: `BGE_RERANKER_INTEGRATION.md`


