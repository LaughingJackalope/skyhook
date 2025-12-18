import pytest
import yaml
import os
from kubernetes import client, config

# Load Kubernetes configuration
config.load_kube_config()
core_v1 = client.CoreV1Api()

def get_expected_namespaces():
    """Parses the namespaces.yaml file to get a list of expected namespaces."""
    # current file is in tests/, so go up one level to root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    namespaces_file = os.path.join(project_root, "platform/00-namespaces/namespaces.yaml")
    
    expected_namespaces = []
    with open(namespaces_file, 'r') as f:
        # Load all documents from the YAML file
        documents = yaml.safe_load_all(f)
        for doc in documents:
            if doc and doc.get('kind') == 'Namespace':
                expected_namespaces.append(doc['metadata']['name'])
    return expected_namespaces

def test_namespaces_exist():
    """Verifies that all namespaces defined in platform/00-namespaces/namespaces.yaml exist in the cluster."""
    expected_namespaces = get_expected_namespaces()
    
    # List actual namespaces in the cluster
    # We simply get all names
    actual_namespaces = [ns.metadata.name for ns in core_v1.list_namespace().items]
    
    missing_namespaces = []
    for ns in expected_namespaces:
        if ns not in actual_namespaces:
            missing_namespaces.append(ns)
            
    assert not missing_namespaces, f"The following expected namespaces are missing from the cluster: {missing_namespaces}"
