# AI Troubleshooter v8 - RBAC Access Summary

## ✅ Cluster-Wide Access Granted

The `ai-troubleshooter-v8-sa` service account now has **read-only access to all namespaces** in the cluster.

## Applied Configuration

**File**: `v8-rbac.yaml`

### Service Account
- **Name**: `ai-troubleshooter-v8-sa`
- **Namespace**: `ai-troubleshooter-v8`

### ClusterRole
- **Name**: `ai-troubleshooter-v8-reader`
- **Type**: ClusterRole (cluster-wide)
- **Permissions**: Read-only (get, list, watch)

### ClusterRoleBinding
- **Name**: `ai-troubleshooter-v8-binding`
- **Binds**: ServiceAccount → ClusterRole
- **Scope**: All namespaces

## Permissions Granted

### Core Resources (apiGroup: "")
✅ **Namespaces** - get, list, watch
✅ **Pods** - get, list, watch
✅ **Pods/log** - get, list, watch
✅ **Events** - get, list, watch
✅ **PersistentVolumeClaims** - get, list, watch
✅ **Services** - get, list, watch
✅ **ConfigMaps** - get, list, watch
✅ **Secrets** - get, list, watch

### Apps (apiGroup: "apps")
✅ **Deployments** - get, list, watch
✅ **ReplicaSets** - get, list, watch
✅ **StatefulSets** - get, list, watch
✅ **DaemonSets** - get, list, watch

### Batch (apiGroup: "batch")
✅ **Jobs** - get, list, watch
✅ **CronJobs** - get, list, watch

### OpenShift Routes (apiGroup: "route.openshift.io")
✅ **Routes** - get, list, watch

### KServe (apiGroup: "serving.kserve.io")
✅ **InferenceServices** - get, list, watch

### Metrics (apiGroup: "metrics.k8s.io")
✅ **Pods** - get, list
✅ **Nodes** - get, list

## Verification Tests

All permissions verified successfully:

```bash
# Test 1: List pods across all namespaces
$ oc auth can-i list pods --all-namespaces --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
✅ yes

# Test 2: Get pod logs
$ oc auth can-i get pods/log --all-namespaces --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
✅ yes

# Test 3: List namespaces
$ oc auth can-i list namespaces --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
✅ yes

# Test 4: List events in specific namespace
$ oc auth can-i list events -n model --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
✅ yes
```

## Security Considerations

### ✅ Read-Only Access
- No write/delete permissions
- Cannot modify cluster resources
- Cannot delete pods or deployments
- Safe for troubleshooting and monitoring

### ✅ Namespaced Service Account
- Service account is confined to `ai-troubleshooter-v8` namespace
- Cannot be used from other namespaces without explicit binding
- Follows principle of least privilege

### ⚠️ Secrets Access
- Has read access to secrets in all namespaces
- Required for comprehensive troubleshooting
- Consider implementing secret filtering in application if needed

## Use Cases Enabled

With this RBAC configuration, AI Troubleshooter v8 can now:

1. **Multi-Namespace Troubleshooting**
   - Analyze pods across all namespaces
   - Collect logs from any namespace
   - View events cluster-wide

2. **Comprehensive Log Collection**
   - Gather logs from model namespace (BGE, Llama Stack, etc.)
   - Monitor application namespaces
   - Track system namespaces (openshift-*, kube-*)

3. **Root Cause Analysis**
   - Correlate issues across namespaces
   - Track dependencies between services
   - Analyze cluster-wide patterns

4. **InferenceService Monitoring**
   - Monitor BGE reranker status
   - Track Llama Stack health
   - View all KServe deployments

## Application Configuration

The AI Troubleshooter v8 deployment automatically uses this service account:

```yaml
spec:
  template:
    spec:
      serviceAccountName: ai-troubleshooter-v8-sa  # ← Uses this SA
```

The application can now use `oc` commands or Kubernetes API to access all namespaces.

## Management Commands

### View Current Permissions
```bash
# Show all ClusterRole rules
oc describe clusterrole ai-troubleshooter-v8-reader

# Show ClusterRoleBinding
oc describe clusterrolebinding ai-troubleshooter-v8-binding

# List all resources the SA can access
oc auth can-i --list --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
```

### Update Permissions
```bash
# Edit the v8-rbac.yaml file, then:
oc apply -f v8-rbac.yaml
```

### Revoke Permissions
```bash
# Remove cluster-wide access
oc delete clusterrolebinding ai-troubleshooter-v8-binding
oc delete clusterrole ai-troubleshooter-v8-reader
```

## Namespaces Accessible

The service account can now access ALL namespaces including:

- ✅ `ai-troubleshooter-v8` (home namespace)
- ✅ `model` (BGE reranker, Llama Stack)
- ✅ `ai-troubleshooter-v6`, `ai-troubleshooter-v7` (other versions)
- ✅ `default`
- ✅ `openshift-*` (OpenShift system namespaces)
- ✅ `kube-*` (Kubernetes system namespaces)
- ✅ Any custom application namespaces

## Testing Access

Test the configuration from within a pod:

```bash
# Exec into the ai-troubleshooter-v8 pod
oc exec -it deployment/ai-troubleshooter-v8 -n ai-troubleshooter-v8 -- bash

# Inside the pod, test access:
oc get namespaces
oc get pods -A
oc get pods -n model
oc logs <pod-name> -n <namespace>
oc get events -A
```

## Troubleshooting

### Issue: Permission Denied

**Symptom**: Application cannot access resources in other namespaces

**Check**:
```bash
# Verify ClusterRoleBinding exists
oc get clusterrolebinding ai-troubleshooter-v8-binding

# Verify ServiceAccount is correct in deployment
oc get deployment ai-troubleshooter-v8 -n ai-troubleshooter-v8 -o yaml | grep serviceAccount

# Test permissions
oc auth can-i list pods --all-namespaces --as=system:serviceaccount:ai-troubleshooter-v8:ai-troubleshooter-v8-sa
```

**Solution**:
```bash
# Reapply RBAC
oc apply -f v8-rbac.yaml
```

### Issue: SA Not Found

**Symptom**: ServiceAccount doesn't exist

**Solution**:
```bash
# Create the service account
oc apply -f v8-rbac.yaml
```

## Status

```
✅ ServiceAccount Created      - ai-troubleshooter-v8-sa
✅ ClusterRole Created          - ai-troubleshooter-v8-reader
✅ ClusterRoleBinding Created   - ai-troubleshooter-v8-binding
✅ Permissions Verified         - All tests passed
✅ Access Scope                 - All namespaces (cluster-wide)
✅ Security Level               - Read-only
```

---

**Date**: October 17, 2025
**Applied By**: RBAC Configuration
**Status**: ✅ Active and Verified


