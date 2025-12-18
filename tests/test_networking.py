import pytest
from kubernetes import client, config

# Load Kubernetes configuration
config.load_kube_config()
core_v1 = client.CoreV1Api()

def test_vpc_cni_running():
    """Verifies that VPC CNI (aws-node) pods are running in kube-system."""
    pods = core_v1.list_namespaced_pod(
        namespace="kube-system", 
        label_selector="k8s-app=aws-node"
    ).items
    
    assert len(pods) > 0, "No aws-node (VPC CNI) pods found"
    
    running_pods = [p for p in pods if p.status.phase == "Running"]
    assert len(running_pods) > 0, "No aws-node pods are in Running state"

def test_lb_controller_running():
    """Verifies that AWS Load Balancer Controller pods are running in kube-system."""
    pods = core_v1.list_namespaced_pod(
        namespace="kube-system", 
        label_selector="app.kubernetes.io/name=aws-load-balancer-controller"
    ).items
    
    assert len(pods) > 0, "No aws-load-balancer-controller pods found"
    
    running_pods = [p for p in pods if p.status.phase == "Running"]
    assert len(running_pods) > 0, "No aws-load-balancer-controller pods are in Running state"

def test_external_dns_running():
    """Verifies that External DNS pods are running in external-dns namespace."""
    pods = core_v1.list_namespaced_pod(
        namespace="external-dns", 
        label_selector="app.kubernetes.io/name=external-dns"
    ).items
    
    assert len(pods) > 0, "No external-dns pods found"
    
    running_pods = [p for p in pods if p.status.phase == "Running"]
    assert len(running_pods) > 0, "No external-dns pods are in Running state"
