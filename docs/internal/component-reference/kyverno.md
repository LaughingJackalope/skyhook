# Kyverno Component Reference

Kyverno is the policy engine for the Skyhook platform, providing automatic configuration injection for HPC workloads.

## Overview

Kyverno mutates pod specifications at admission time to inject required configuration, eliminating the need for researchers to understand infrastructure details.

## Directory Structure

```
platform/base/kyverno/
├── helmrelease.yaml                    # Kyverno Helm deployment
├── kustomization.yaml                  # Kustomize wrapper
└── policies/
    ├── inject-efa-env.yaml             # EFA environment injection
    └── inject-hpc-tolerations.yaml     # HPC toleration injection
```

## Deployment

Kyverno is deployed via Flux HelmRelease:

- **Chart**: `kyverno/kyverno` v3.2.7
- **Namespace**: `kyverno`
- **Replicas**: 3 admission controllers, 2 background/cleanup/reports controllers

## Policies

### inject-efa-env

**Status**: Implemented and verified

**Purpose**: Automatically inject EFA environment variables when pods request EFA resources.

**Trigger**: Pod container requests `vpc.amazonaws.com/efa` resource limit

**Injected Variables**:
| Variable | Value | Purpose |
|----------|-------|---------|
| `FI_PROVIDER` | `efa` | Use EFA libfabric provider |
| `FI_EFA_USE_DEVICE_RDMA` | `1` | Enable RDMA |
| `NCCL_DEBUG` | `INFO` | NCCL debug logging |
| `NCCL_PROTO` | `simple` | NCCL protocol for EFA |

**Why This Matters**: Without these variables, NCCL silently falls back to TCP networking, running ~10x slower with no error messages.

**Example Pod** (before mutation):
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: training-job
spec:
  containers:
  - name: trainer
    image: pytorch/pytorch:latest
    resources:
      limits:
        vpc.amazonaws.com/efa: "4"
```

**After Mutation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: training-job
spec:
  containers:
  - name: trainer
    image: pytorch/pytorch:latest
    env:
    - name: FI_PROVIDER
      value: "efa"
    - name: FI_EFA_USE_DEVICE_RDMA
      value: "1"
    - name: NCCL_DEBUG
      value: "INFO"
    - name: NCCL_PROTO
      value: "simple"
    resources:
      limits:
        vpc.amazonaws.com/efa: "4"
```

### inject-hpc-tolerations

**Status**: Implemented and verified

**Purpose**: Add HPC node tolerations and node selector when pods are annotated for HPC scheduling.

**Trigger**: Pod has annotation `skypilot.co/hpc: "true"`

**Injected Configuration**:
- Toleration for `nvidia.com/gpu:NoSchedule`
- Toleration for `skyhook.io/workload=hpc:NoSchedule`
- NodeSelector `skyhook.io/tier: hpc`

**Example Pod** (before mutation):
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: distributed-training
  annotations:
    skypilot.co/hpc: "true"
spec:
  containers:
  - name: trainer
    image: pytorch/pytorch:latest
```

**After Mutation**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: distributed-training
  annotations:
    skypilot.co/hpc: "true"
spec:
  tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
  - key: skyhook.io/workload
    operator: Equal
    value: hpc
    effect: NoSchedule
  nodeSelector:
    skyhook.io/tier: hpc
  containers:
  - name: trainer
    image: pytorch/pytorch:latest
```

### kyverno-image-signing (Deferred)

**Status**: Not implemented

**Purpose**: Enforce container image signing requirements.

**Notes**: Requires registry configuration and signing key setup before implementation.

## Operations

### Verify Policy Status

```bash
# List all policies
kubectl get clusterpolicy

# Check specific policy
kubectl get clusterpolicy inject-efa-env -o yaml
```

### Test Policy Mutation

```bash
# Create test pod requesting EFA
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: test-efa
spec:
  containers:
  - name: test
    image: busybox
    command: ["sleep", "infinity"]
    resources:
      limits:
        vpc.amazonaws.com/efa: "1"
  restartPolicy: Never
EOF

# Verify env vars injected
kubectl get pod test-efa -o jsonpath='{.spec.containers[0].env}' | jq .

# Cleanup
kubectl delete pod test-efa
```

### Debug Policy Issues

```bash
# Check Kyverno admission controller logs
kubectl logs -n kyverno -l app.kubernetes.io/component=admission-controller

# View policy reports (if background scanning enabled)
kubectl get policyreport -A

# Check webhook configuration
kubectl get mutatingwebhookconfiguration kyverno-resource-mutating-webhook-cfg -o yaml
```

### Common Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Env vars not injected | Pod doesn't request EFA resource | Add `vpc.amazonaws.com/efa` to limits |
| Tolerations not added | Missing annotation | Add `skypilot.co/hpc: "true"` annotation |
| Policy not ready | Kyverno unhealthy | Check `kubectl get pods -n kyverno` |
| Webhook timeout | Kyverno overloaded | Scale admission controller replicas |

## Monitoring

Kyverno exposes Prometheus metrics. ServiceMonitors are enabled by default.

Key metrics:
- `kyverno_admission_review_duration_seconds` — Admission latency
- `kyverno_policy_results_total` — Policy evaluation results
- `kyverno_policy_execution_duration_seconds` — Policy execution time

## Related

- [ADR-002: Kyverno Policies](../adrs/002-kyverno-policies.md)
- [SkyPilot Infrastructure Reference](skypilot-infra.md)
- [Implementation Plan: Automation](../design/implementation-plan.md#6-automation-kyverno)

