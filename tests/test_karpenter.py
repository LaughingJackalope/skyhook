import pytest
from kubernetes import client, config
import time
import yaml

# Load Kubernetes configuration
config.load_kube_config()
core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def create_namespace(namespace):
    """Creates a Kubernetes namespace."""
    try:
        core_v1.create_namespace(
            client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        )
    except client.ApiException as e:
        if e.status != 409:  # Ignore "Conflict" errors if namespace already exists
            raise

def delete_namespace(namespace):
    """Deletes a Kubernetes namespace."""
    try:
        core_v1.delete_namespace(name=namespace, body=client.V1DeleteOptions())
    except client.ApiException as e:
        if e.status != 404:  # Ignore "Not Found" errors
            raise

def create_deployment(namespace, deployment_name, node_selector):
    """Creates a Kubernetes deployment with a node selector."""
    container = client.V1Container(
        name="test-container",
        image="nginx",
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "100Mi"}
        ),
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": deployment_name},
            annotations={"eks.amazonaws.com/skip-pod-identity-webhook": "true"},
        ),
        spec=client.V1PodSpec(
            containers=[container],
            node_selector=node_selector,
        ),
    )
    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={"matchLabels": {"app": deployment_name}},
    )
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=spec,
    )
    apps_v1.create_namespaced_deployment(
        namespace=namespace, body=deployment
    )

def delete_deployment(namespace, deployment_name):
    """Deletes a Kubernetes deployment."""
    try:
        apps_v1.delete_namespaced_deployment(
            name=deployment_name,
            namespace=namespace,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground", grace_period_seconds=5
            ),
        )
    except client.ApiException as e:
        if e.status != 404:
            raise

def wait_for_pod_to_be_running(namespace, deployment_name, timeout=300):
    """Waits for a pod in a deployment to be in the 'Running' phase."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        pods = core_v1.list_namespaced_pod(
            namespace=namespace, label_selector=f"app={deployment_name}"
        ).items
        if pods and pods[0].status.phase == "Running":
            return pods[0]
        time.sleep(5)

    # If the pod is not running after the timeout, print debug information
    if pods:
        pod = pods[0]
        print(f"Pod {pod.metadata.name} status: {pod.status.phase}")
        print("Pod events:")
        events = core_v1.list_namespaced_event(
            namespace=namespace, field_selector=f"involvedObject.name={pod.metadata.name}"
        ).items
        for event in events:
            print(f"- {event.type}: {event.reason} - {event.message}")
            
    raise TimeoutError(f"Pod for deployment {deployment_name} did not start in time.")

def get_node_for_pod(pod):
    """Gets the node that a pod is scheduled on."""
    return core_v1.read_node(pod.spec.node_name)


def create_gpu_deployment(namespace, deployment_name, node_selector, gpu_count="1"):
    """Creates a Kubernetes deployment with a node selector and GPU requirements."""
    container = client.V1Container(
        name="test-container",
        image="nvidia/cuda:11.4.2-base-ubuntu20.04",
        command=["/bin/sh", "-c", "sleep 100000"],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "100Mi", "nvidia.com/gpu": gpu_count},
            limits={"nvidia.com/gpu": gpu_count},
        ),
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": deployment_name}),
        spec=client.V1PodSpec(
            containers=[container],
            node_selector=node_selector,
        ),
    )
    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={"matchLabels": {"app": deployment_name}},
    )
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=deployment_name),
        spec=spec,
    )
    apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)


def delete_all_deployments(namespace):
    """Deletes all deployments in a Kubernetes namespace."""
    try:
        apps_v1.delete_collection_namespaced_deployment(namespace=namespace)
    except client.ApiException as e:
        if e.status != 404:
            raise


@pytest.fixture(scope="function")
def test_namespace(request):
    """Pytest fixture to create and delete a test namespace for each test function."""
    namespace = "karpenter-conformance-testing"
    create_namespace(namespace)

    def finalizer():
        delete_all_deployments(namespace)
        delete_namespace(namespace)

    request.addfinalizer(finalizer)
    return namespace


class TestKarpenterConformance:
    def test_general_purpose_nodepool(self, test_namespace):
        """
        Tests the 'general-purpose' NodePool.
        Deploys a pod that should be scheduled on a node from this pool.
        """
        deployment_name = "test-general-purpose"
        node_selector = {"skyhook.io/pool": "general-purpose"}
        create_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name)
            node = get_node_for_pod(pod)

            # Assert that the node has the correct labels
            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "general"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "general-purpose"

            # Assert that the node has the correct instance type
            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith("m")

        finally:
            delete_deployment(test_namespace, deployment_name)

    def test_compute_optimized_nodepool(self, test_namespace):
        """
        Tests the 'compute-optimized' NodePool.
        """
        deployment_name = "test-compute-optimized"
        node_selector = {"skyhook.io/pool": "compute-optimized"}
        create_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "general"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "compute-optimized"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith("c")

        finally:
            delete_deployment(test_namespace, deployment_name)

    def test_memory_optimized_nodepool(self, test_namespace):
        """
        Tests the 'memory-optimized' NodePool.
        """
        deployment_name = "test-memory-optimized"
        node_selector = {"skyhook.io/pool": "memory-optimized"}
        create_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "general"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "memory-optimized"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith("r")

        finally:
            delete_deployment(test_namespace, deployment_name)
    
    def test_batch_processing_nodepool(self, test_namespace):
        """
        Tests the 'batch-processing' NodePool.
        """
        deployment_name = "test-batch-processing"
        node_selector = {"skyhook.io/pool": "batch-processing"}
        create_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name, timeout=600)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "batch"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "batch-processing"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith(("m5", "c5", "r5"))
            
            assert "karpenter.sh/capacity-type" in node.metadata.labels
            assert node.metadata.labels["karpenter.sh/capacity-type"] == "spot"

        finally:
            delete_deployment(test_namespace, deployment_name)

    def test_gpu_standard_nodepool(self, test_namespace):
        """
        Tests the 'gpu-standard' NodePool.
        """
        deployment_name = "test-gpu-standard"
        node_selector = {"skyhook.io/pool": "gpu-standard"}
        create_gpu_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name, timeout=600)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "gpu"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "gpu-standard"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith(("g", "p"))

            assert "karpenter.sh/capacity-type" in node.metadata.labels
            assert node.metadata.labels["karpenter.sh/capacity-type"] == "on-demand"
            
            # Check for the taint
            assert any(
                taint.key == "nvidia.com/gpu" and taint.effect == "NoSchedule"
                for taint in node.spec.taints
            )

        finally:
            delete_deployment(test_namespace, deployment_name)
    
    def test_gpu_spot_nodepool(self, test_namespace):
        """
        Tests the 'gpu-spot' NodePool.
        """
        deployment_name = "test-gpu-spot"
        node_selector = {"skyhook.io/pool": "gpu-spot"}
        create_gpu_deployment(test_namespace, deployment_name, node_selector)

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name, timeout=600)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "gpu"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "gpu-spot"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith("g")

            assert "karpenter.sh/capacity-type" in node.metadata.labels
            assert node.metadata.labels["karpenter.sh/capacity-type"] == "spot"
            
            # Check for the taints
            assert any(
                taint.key == "nvidia.com/gpu" and taint.effect == "NoSchedule"
                for taint in node.spec.taints
            )
            assert any(
                taint.key == "karpenter.sh/capacity-type" and taint.value == "spot" and taint.effect == "NoSchedule"
                for taint in node.spec.taints
            )

        finally:
            delete_deployment(test_namespace, deployment_name)
            
    def test_hpc_distributed_nodepool(self, test_namespace):
        """
        Tests the 'hpc-distributed' NodePool.
        """
        deployment_name = "test-hpc-distributed"
        node_selector = {"skyhook.io/pool": "hpc-distributed"}
        create_gpu_deployment(test_namespace, deployment_name, node_selector, gpu_count="4")

        try:
            pod = wait_for_pod_to_be_running(test_namespace, deployment_name, timeout=900)
            node = get_node_for_pod(pod)

            assert "skyhook.io/tier" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/tier"] == "hpc"
            assert "skyhook.io/pool" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/pool"] == "hpc-distributed"

            assert "node.kubernetes.io/instance-type" in node.metadata.labels
            instance_type = node.metadata.labels["node.kubernetes.io/instance-type"]
            assert instance_type.startswith(("p4d", "p4de", "p5"))
            
            assert "karpenter.sh/capacity-type" in node.metadata.labels
            assert node.metadata.labels["karpenter.sh/capacity-type"] == "on-demand"

            # Check for the taints
            assert any(
                taint.key == "nvidia.com/gpu" and taint.effect == "NoSchedule"
                for taint in node.spec.taints
            )
            assert any(
                taint.key == "skyhook.io/workload" and taint.value == "hpc" and taint.effect == "NoSchedule"
                for taint in node.spec.taints
            )
            
            # Check for EFA tag
            assert "skyhook.io/efa-enabled" in node.metadata.labels
            assert node.metadata.labels["skyhook.io/efa-enabled"] == "true"
            
            # A simple check to see if FSx is mounted. This is not a foolproof check.
            # A better check would be to exec into the pod and check for the mount.
            # For now, we will just check if the userdata tried to mount it.
            # This requires access to the EC2 instance metadata, which is not directly
            # available via the kubernetes API. We will skip this check for now.


        finally:
            delete_deployment(test_namespace, deployment_name)

