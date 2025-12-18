# Platform Base Reference

Documentation for the `platform/base/` directory containing Flux HelmReleases for platform services.

## Component Versions

| Component | Version | Status | Purpose |
|-----------|---------|--------|---------|
| Karpenter | 1.2.0 | Ready | Node provisioning |
| AWS Load Balancer Controller | 1.9.2 | Ready | ALB/NLB provisioning |
| Node Termination Handler | 0.21.0 | Ready | Spot interruption handling |
| kube-prometheus-stack | 61.2.0 | Ready | Observability stack |
| DCGM Exporter | 3.4.2 | Ready | GPU metrics |
| FSx CSI Driver | 1.6.1 | Ready | Lustre storage |
| EFS CSI Driver | 2.5.5 | Ready | Shared filesystem |
| Gatekeeper | 3.15.1 | Ready | Policy enforcement |
| KEDA | 2.14.0 | Ready | Event-driven autoscaling |
| Secrets Store CSI | 1.4.5 | Ready | Secrets integration |

## Directory Structure

```
platform/base/
├── cni/                         # VPC CNI configuration
│   ├── helmrelease.yaml
│   └── kustomization.yaml
├── csi-ebs/                     # EBS CSI driver
├── csi-efs/                     # EFS CSI driver
├── csi-fsx/                     # FSx CSI driver
├── dcgm-exporter/               # NVIDIA GPU metrics
│   ├── helmrelease.yaml
│   └── kustomization.yaml
├── external-dns/                # DNS automation
├── gatekeeper/                  # OPA Gatekeeper
├── karpenter/                   # Node provisioning
│   ├── helmrelease.yaml         # Karpenter controller (v1.2.0)
│   ├── ec2nodeclasses.yaml      # AWS node configurations
│   ├── nodepools.yaml           # Provisioning policies
│   └── kustomization.yaml
├── keda/                        # Event-driven autoscaling
├── load-balancer/               # AWS Load Balancer Controller
├── logging/                     # Fluent Bit logging
├── node-termination-handler/    # Spot interruption handling
│   ├── helmrelease.yaml
│   └── kustomization.yaml
├── observability/               # Prometheus/Grafana stack
├── secrets-store-csi/           # AWS Secrets Manager integration
├── sources/                     # Helm repositories
│   ├── helmrepositories.yaml
│   └── kustomization.yaml
├── kustomization.yaml           # Root kustomization
└── namespaces.yaml              # Platform namespaces
```

## Component Overview

### CNI (`cni/`)

**Chart**: AWS VPC CNI

**Purpose**: Pod networking with VPC integration, EFA support.

**Key Configuration**:
- Prefix delegation for IP efficiency
- EFA plugin enabled
- Custom networking mode

### CSI Drivers

#### `csi-ebs/`
**Chart**: AWS EBS CSI Driver  
**Purpose**: Dynamic EBS volume provisioning

#### `csi-efs/`
**Chart**: AWS EFS CSI Driver  
**Purpose**: Shared EFS filesystem access

#### `csi-fsx/`
**Chart**: AWS FSx CSI Driver (v1.6.1)  
**Purpose**: FSx for Lustre integration

**Key for Skyhook**: Enables FSx mounts at `/mnt/fsx` for high-performance shared storage.

### Karpenter (`karpenter/`)

**Chart**: Karpenter (v1.2.0)

**Purpose**: Just-in-time node provisioning with tiered NodePools

**Files**:
- `helmrelease.yaml`: Karpenter controller deployment
- `ec2nodeclasses.yaml`: Three node classes (default, gpu, hpc)
- `nodepools.yaml`: Six tiered NodePools

**NodePool Architecture**:

| NodePool | EC2NodeClass | Instance Types | Capacity |
|----------|--------------|----------------|----------|
| general-purpose | default | m5, m6i, m7i | spot+od |
| compute-optimized | default | c5, c6i, c7i | spot+od |
| memory-optimized | default | r5, r6i, r7i | spot+od |
| gpu-standard | gpu | g5, p4d, p5 | on-demand |
| gpu-spot | gpu | g5, g4dn | spot |
| hpc-distributed | hpc | p4d, p5 | on-demand |

**EC2NodeClass Configuration**:
- `default`: System subnets, AL2023 AMI, general workloads
- `gpu`: HPC subnets, AL2 AMI, GPU workloads
- `hpc`: HPC subnets, EFA-enabled, FSx mount scripts

### Node Termination Handler (`node-termination-handler/`)

**Chart**: AWS Node Termination Handler (v0.21.0)

**Purpose**: Gracefully handle spot interruptions, scheduled events, and instance state changes.

**Key Features**:
- SQS-based event delivery
- Pod draining before termination
- Webhook notifications

### DCGM Exporter (`dcgm-exporter/`)

**Chart**: NVIDIA DCGM Exporter (v3.4.2)

**Purpose**: Export NVIDIA GPU metrics to Prometheus

**Metrics Exposed**:
- GPU utilization, memory usage, temperature
- SM clock, memory clock
- Power usage, PCIe throughput

### Logging (`logging/`)

**Chart**: Fluent Bit

**Purpose**: Log collection and routing

**Key Configuration for Skyhook**:
- Task-based log tagging (SkyPilot labels → CloudWatch streams)
- S3 archival for log backup
- Spot interruption flush handling

**Fluent Bit Pipeline**:
```
Input (container logs)
    ↓
Kubernetes Metadata Filter
    ↓
Rewrite Tag (extract skypilot.task_id)
    ↓
CloudWatch Output (/skypilot/user-jobs/task-*)
    ↓
S3 Output (archive)
```

### Observability (`observability/`)

**Chart**: kube-prometheus-stack (v61.2.0)

**Purpose**: Metrics collection, alerting, dashboards

**Key Components**:
- Prometheus: Metrics collection
- Grafana: Dashboards
- AlertManager: Alert routing
- DCGM Exporter integration for GPU metrics

### Load Balancer (`load-balancer/`)

**Chart**: AWS Load Balancer Controller (v1.9.2)

**Purpose**: ALB/NLB provisioning for ingress

**Note**: All ingress uses ALB with ACM certificates (no cert-manager needed).

### Secrets Store CSI (`secrets-store-csi/`)

**Chart**: Secrets Store CSI Driver + AWS Provider (v1.4.5)

**Purpose**: Mount AWS Secrets Manager secrets as volumes

### Sources (`sources/`)

**Purpose**: Helm repository definitions (OCI and traditional)

**Repositories**:
- `aws-eks-charts`: AWS EKS charts
- `karpenter`: Karpenter OCI registry (public.ecr.aws/karpenter)
- `nvidia`: NVIDIA GPU charts
- `fluent`: Fluent Bit
- `prometheus-community`: kube-prometheus-stack

## Kustomization Structure

The root `kustomization.yaml` includes all components:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespaces.yaml
  - sources
  - cni
  - csi-ebs
  - csi-efs
  - csi-fsx
  - load-balancer
  - external-dns
  - keda
  - observability
  - logging
  - secrets-store-csi
  - gatekeeper
  - karpenter
  - node-termination-handler
  - dcgm-exporter
```

## HelmRelease Pattern

All components follow a consistent HelmRelease pattern:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta2
kind: HelmRelease
metadata:
  name: <component>
  namespace: flux-system
spec:
  interval: 10m
  releaseName: <component>
  targetNamespace: <target-namespace>
  install:
    createNamespace: true
  chart:
    spec:
      chart: <chart-name>
      version: <version>
      sourceRef:
        kind: HelmRepository
        name: <repo-name>
        namespace: flux-system
  values:
    # Component-specific configuration
```

> **Note**: The `v2beta2` API is deprecated. Upgrade to `v2` when Flux is updated.

## Common Operations

### Updating a Component

1. Find the HelmRelease in `platform/base/<component>/`
2. Update `spec.chart.spec.version` or `spec.values`
3. Commit and push
4. Flux reconciles automatically

### Checking Component Status

```bash
# View all HelmReleases
kubectl get helmreleases -n flux-system

# Check specific component
kubectl get helmrelease -n flux-system <name>

# View detailed status
kubectl describe helmrelease -n flux-system <name>

# Check Karpenter NodePools
kubectl get nodepools,ec2nodeclasses
```

### Troubleshooting Failed Releases

```bash
# Check Helm history
helm history <release-name> -n <namespace>

# View release values
helm get values <release-name> -n <namespace>

# Force reconciliation
kubectl annotate helmrelease <name> -n flux-system \
  reconcile.fluxcd.io/requestedAt="$(date +%s)" --overwrite

# Manual rollback (if needed)
helm rollback <release-name> <revision> -n <namespace>
```

## Related

- [Component Reference Index](index.md)
- [SkyPilot Infra](skypilot-infra.md)
- [Control Plane](control-plane.md)
- [Karpenter Operations Runbook](../runbooks/karpenter-ops.md)
