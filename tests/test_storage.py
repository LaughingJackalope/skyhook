import pytest
import yaml
import os
from kubernetes import client, config

# Load Kubernetes configuration
config.load_kube_config()
core_v1 = client.CoreV1Api()
storage_v1 = client.StorageV1Api()

def get_ebs_expected_storage_classes():
    """Parses ebs-csi-values.yaml to get expected StorageClasses."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    values_file = os.path.join(project_root, "platform/01-storage/ebs-csi-values.yaml")
    
    expected_scs = []
    with open(values_file, 'r') as f:
        values = yaml.safe_load(f)
        sc_configs = values.get('storageClasses', [])
        for sc in sc_configs:
            expected_scs.append(sc['name'])
    return expected_scs

def test_csi_drivers_running():
    """Verifies that the expected CSI driver pods are running in kube-system."""
    expected_drivers = [
        {"label": "app.kubernetes.io/name=aws-ebs-csi-driver", "name": "EBS CSI"},
        {"label": "app.kubernetes.io/name=aws-fsx-csi-driver", "name": "FSx CSI"},
        {"label": "app.kubernetes.io/name=aws-efs-csi-driver", "name": "EFS CSI"}
    ]
    
    for driver in expected_drivers:
        pods = core_v1.list_namespaced_pod(
            namespace="kube-system", 
            label_selector=driver["label"]
        ).items
        
        assert len(pods) > 0, f"No pods found for {driver['name']} (label: {driver['label']})"
        
        # Check if at least one pod is running
        running_pods = [p for p in pods if p.status.phase == "Running"]
        assert len(running_pods) > 0, f"{driver['name']} pods are not in Running state"

def test_ebs_storage_classes_exist():
    """Verifies that StorageClasses defined in ebs-csi-values.yaml exist."""
    expected_scs = get_ebs_expected_storage_classes()
    actual_scs = [sc.metadata.name for sc in storage_v1.list_storage_class().items]
    
    missing_scs = [sc for sc in expected_scs if sc not in actual_scs]
    assert not missing_scs, f"The following expected EBS StorageClasses are missing: {missing_scs}"
