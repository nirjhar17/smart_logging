#!/bin/bash
# Deploy AI Troubleshooter v8 with NVIDIA's Hybrid Retrieval Approach

set -e

echo "🚀 Deploying AI Troubleshooter v8 - NVIDIA Approach"
echo "=================================================="

NAMESPACE="ai-troubleshooter-v8"
APP_NAME="ai-troubleshooter-v8"

# Check if namespace exists
echo "📍 Checking namespace..."
if ! oc get namespace $NAMESPACE &> /dev/null; then
    echo "Creating namespace $NAMESPACE..."
    oc create namespace $NAMESPACE
fi

# Switch to namespace
oc project $NAMESPACE

echo ""
echo "📦 Creating ConfigMap with application code..."

# Create ConfigMap with all Python files
oc create configmap ${APP_NAME}-nvidia-code \
    --from-file=k8s_log_fetcher.py=./k8s_log_fetcher.py \
    --from-file=k8s_hybrid_retriever.py=./k8s_hybrid_retriever.py \
    --from-file=v8_streamlit_nvidia_app.py=./v8_streamlit_nvidia_app.py \
    --dry-run=client -o yaml | oc apply -f -

echo "✅ ConfigMap created/updated"

echo ""
echo "🔐 Applying RBAC configuration..."
oc apply -f v8-rbac.yaml

echo ""
echo "🚀 Applying Deployment, Service, and Route..."
cat <<EOF | oc apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}-nvidia
  namespace: ${NAMESPACE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${APP_NAME}-nvidia
  template:
    metadata:
      labels:
        app: ${APP_NAME}-nvidia
    spec:
      serviceAccountName: ${APP_NAME}-sa
      containers:
      - name: streamlit-app
        image: python:3.11-slim
        ports:
        - containerPort: 8501
          name: http
        env:
        - name: LLAMA_STACK_URL
          value: "http://llama-stack-service.ai-troubleshooter-v8.svc.cluster.local:8321"
        - name: PYTHONUNBUFFERED
          value: "1"
        command: ["/bin/bash", "-c"]
        args:
          - |
            set -e
            echo "🔧 Installing dependencies..."
            pip install --no-cache-dir streamlit llama-stack-client langchain langchain-community faiss-cpu rank-bm25
            
            echo "📂 Copying application files..."
            cp /app-code/* /app/
            cd /app
            
            echo "🚀 Starting Streamlit app..."
            streamlit run v8_streamlit_nvidia_app.py \
              --server.port=8501 \
              --server.address=0.0.0.0 \
              --server.headless=true \
              --server.fileWatcherType=none \
              --browser.gatherUsageStats=false
        volumeMounts:
        - name: app-code
          mountPath: /app-code
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: app-code
        configMap:
          name: ${APP_NAME}-nvidia-code
---
apiVersion: v1
kind: Service
metadata:
  name: ${APP_NAME}-nvidia-service
  namespace: ${NAMESPACE}
spec:
  selector:
    app: ${APP_NAME}-nvidia
  ports:
  - name: http
    port: 8501
    targetPort: 8501
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: ${APP_NAME}-nvidia
  namespace: ${NAMESPACE}
spec:
  to:
    kind: Service
    name: ${APP_NAME}-nvidia-service
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Checking deployment status..."
oc get pods -n $NAMESPACE | grep "${APP_NAME}-nvidia" || echo "Waiting for pods..."

echo ""
echo "🌐 Getting application URL..."
ROUTE_URL=$(oc get route ${APP_NAME}-nvidia -n $NAMESPACE -o jsonpath='{.spec.host}' 2>/dev/null || echo "Route not ready yet")

if [ "$ROUTE_URL" != "Route not ready yet" ]; then
    echo "✅ Application URL: https://$ROUTE_URL"
else
    echo "⏳ Route not ready yet. Check with: oc get route ${APP_NAME}-nvidia -n $NAMESPACE"
fi

echo ""
echo "📝 Useful commands:"
echo "  View logs:    oc logs -f deployment/${APP_NAME}-nvidia -n $NAMESPACE"
echo "  Get pods:     oc get pods -n $NAMESPACE"
echo "  Get route:    oc get route ${APP_NAME}-nvidia -n $NAMESPACE"
echo "  Delete app:   oc delete deployment,service,route -l app=${APP_NAME}-nvidia -n $NAMESPACE"
echo ""
echo "🎉 Done!"


