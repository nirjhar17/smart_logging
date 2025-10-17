#!/bin/bash
# Deploy AI Troubleshooter v8 with Chat Interface

set -e

echo "=================================================="
echo "  AI Troubleshooter v8 - Chat Interface Deploy"
echo "=================================================="
echo

NAMESPACE="ai-troubleshooter-v8"

# Check if we're in the right directory
if [ ! -f "v8_streamlit_chat_app.py" ]; then
    echo "❌ Error: v8_streamlit_chat_app.py not found"
    echo "   Please run this script from the ai-troubleshooter-v8 directory"
    exit 1
fi

# Check if oc is available
if ! command -v oc &> /dev/null; then
    echo "❌ Error: oc command not found"
    echo "   Please install OpenShift CLI"
    exit 1
fi

# Check if logged in
if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged in to OpenShift"
    echo "   Please run: oc login"
    exit 1
fi

echo "✅ Prerequisites check passed"
echo

# Confirm namespace
echo "📍 Target namespace: $NAMESPACE"
oc get namespace $NAMESPACE &> /dev/null || {
    echo "❌ Error: Namespace $NAMESPACE does not exist"
    exit 1
}
echo "✅ Namespace exists"
echo

# Backup existing configmap
echo "📦 Backing up existing ConfigMap..."
oc get configmap ai-troubleshooter-v8-code -n $NAMESPACE -o yaml > backup-configmap-$(date +%Y%m%d-%H%M%S).yaml 2>/dev/null || true
echo "✅ Backup complete (if ConfigMap existed)"
echo

# Create new configmap with chat interface
echo "🔧 Creating ConfigMap with chat interface..."
oc create configmap ai-troubleshooter-v8-code \
  --from-file=app.py=v8_streamlit_chat_app.py \
  --from-file=v7_main_graph.py \
  --from-file=v7_graph_nodes.py \
  --from-file=v7_graph_edges.py \
  --from-file=v7_state_schema.py \
  --from-file=v7_hybrid_retriever.py \
  --from-file=v7_bge_reranker.py \
  --from-file=v7_log_collector.py \
  -n $NAMESPACE \
  --dry-run=client -o yaml | oc apply -f -

echo "✅ ConfigMap updated"
echo

# Update deployment if needed
if [ -f "v7-deployment.yaml" ]; then
    echo "🚀 Applying deployment configuration..."
    oc apply -f v7-deployment.yaml -n $NAMESPACE
    echo "✅ Deployment configuration applied"
    echo
fi

# Restart deployment
echo "🔄 Restarting deployment to pick up changes..."
oc rollout restart deployment/ai-troubleshooter-v8 -n $NAMESPACE

echo "⏳ Waiting for rollout to complete..."
oc rollout status deployment/ai-troubleshooter-v8 -n $NAMESPACE

echo
echo "✅ Deployment complete!"
echo

# Get route URL
ROUTE_URL=$(oc get route ai-troubleshooter-v8 -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null)
if [ -n "$ROUTE_URL" ]; then
    echo "=================================================="
    echo "  🌐 Access your Chat Interface:"
    echo "     https://$ROUTE_URL"
    echo "=================================================="
else
    echo "⚠️  Warning: Could not retrieve route URL"
    echo "   Run: oc get route -n $NAMESPACE"
fi

echo
echo "📊 Check pod status:"
echo "   oc get pods -n $NAMESPACE -l app=ai-troubleshooter-v8"
echo
echo "📝 View logs:"
echo "   oc logs -f deployment/ai-troubleshooter-v8 -n $NAMESPACE"
echo
echo "🎉 Deployment complete! Start chatting with your cluster!"
echo


