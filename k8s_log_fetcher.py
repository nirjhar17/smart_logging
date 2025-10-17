"""
K8s Log Fetcher - Fetch logs from OpenShift/Kubernetes pods
Adapted for NVIDIA-style in-memory retrieval approach
"""

import subprocess
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class K8sLogFetcher:
    """
    Fetch logs from OpenShift/Kubernetes pods using oc/kubectl commands
    """
    
    def __init__(self, use_oc: bool = True):
        """
        Initialize log fetcher
        
        Args:
            use_oc: Use 'oc' command (OpenShift) vs 'kubectl' (vanilla K8s)
        """
        self.cli = "oc" if use_oc else "kubectl"
        
    def fetch_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        tail: Optional[int] = None,
        previous: bool = False
    ) -> str:
        """
        Fetch logs from a specific pod
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            container: Container name (optional, uses first container if not specified)
            tail: Number of lines to fetch (optional, fetches all if not specified)
            previous: Fetch logs from previous terminated container
            
        Returns:
            Log content as string
        """
        cmd = [self.cli, "logs", "-n", namespace, pod_name]
        
        if container:
            cmd.extend(["-c", container])
            
        if tail:
            cmd.extend(["--tail", str(tail)])
            
        if previous:
            cmd.append("--previous")
            
        try:
            logger.info(f"Fetching logs: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to fetch logs: {result.stderr}")
                return f"Error fetching logs: {result.stderr}"
                
            return result.stdout
            
        except subprocess.TimeoutExpired:
            logger.error("Log fetch timeout")
            return "Error: Log fetch timeout"
        except Exception as e:
            logger.error(f"Error fetching logs: {e}")
            return f"Error: {str(e)}"
            
    def fetch_namespace_logs(
        self,
        namespace: str,
        label_selector: Optional[str] = None,
        tail_per_pod: int = 1000
    ) -> Dict[str, str]:
        """
        Fetch logs from all pods in a namespace
        
        Args:
            namespace: Kubernetes namespace
            label_selector: Label selector to filter pods (e.g., "app=myapp")
            tail_per_pod: Number of lines to fetch per pod
            
        Returns:
            Dictionary mapping pod names to their log content
        """
        # Get list of pods
        cmd = [self.cli, "get", "pods", "-n", namespace, "-o", "name"]
        
        if label_selector:
            cmd.extend(["-l", label_selector])
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to list pods: {result.stderr}")
                return {}
                
            pod_names = [
                line.replace("pod/", "").strip() 
                for line in result.stdout.strip().split("\n") 
                if line.strip()
            ]
            
            # Fetch logs from each pod
            logs_dict = {}
            for pod_name in pod_names:
                logs = self.fetch_pod_logs(
                    namespace=namespace,
                    pod_name=pod_name,
                    tail=tail_per_pod
                )
                logs_dict[pod_name] = logs
                
            return logs_dict
            
        except Exception as e:
            logger.error(f"Error fetching namespace logs: {e}")
            return {}
            
    def fetch_logs_as_text(
        self,
        namespace: str,
        pod_name: Optional[str] = None,
        label_selector: Optional[str] = None,
        tail: int = 5000
    ) -> str:
        """
        Fetch logs and return as single text document
        (Ready for chunking and indexing NVIDIA-style)
        
        Args:
            namespace: Kubernetes namespace
            pod_name: Specific pod name (optional)
            label_selector: Label selector for multiple pods (optional)
            tail: Number of lines per pod
            
        Returns:
            All logs concatenated as single string
        """
        if pod_name:
            # Single pod
            logs = self.fetch_pod_logs(namespace, pod_name, tail=tail)
            return f"=== Pod: {pod_name} ===\n{logs}\n"
        else:
            # Multiple pods
            logs_dict = self.fetch_namespace_logs(
                namespace=namespace,
                label_selector=label_selector,
                tail_per_pod=tail
            )
            
            # Concatenate all logs
            combined = []
            for pod_name, logs in logs_dict.items():
                combined.append(f"=== Pod: {pod_name} ===")
                combined.append(logs)
                combined.append("")
                
            return "\n".join(combined)


