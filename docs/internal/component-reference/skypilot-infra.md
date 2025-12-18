# SkyPilot Infrastructure Reference

> **Note**: Kyverno policies have been moved to `platform/base/kyverno/`. See [Kyverno Component Reference](kyverno.md) for policy documentation.

Documentation for SkyPilot cluster configurations and Karpenter provisioners.

## Karpenter Configuration

Karpenter resources are now managed in `platform/base/karpenter/`:

```
platform/base/karpenter/
├── ec2nodeclasses.yaml    # EC2 node configurations (default, gpu, hpc)
├── helmrelease.yaml       # Karpenter Helm deployment
├── kustomization.yaml     # Kustomize wrapper
└── nodepools.yaml         # NodePool definitions by tier
```

### EC2NodeClasses

Three node classes are defined:

| Class | Purpose | Subnets | Key Features |
|-------|---------|---------|--------------|
| `default` | General workloads | `skyhook.io/subnet-role: system` | Standard EBS, gp3 storage |
| `gpu` | GPU workloads | `skyhook.io/subnet-role: hpc` | GPU AMI family, larger root volume |
| `hpc` | Distributed training | `skyhook.io/subnet-role: hpc` | EFA enabled, NVMe ephemeral storage |

### NodePools

Six pools covering the workload spectrum:

| Pool | Tier | Capacity | Taints |
|------|------|----------|--------|
| `general-purpose` | general | spot/on-demand | none |
| `compute-optimized` | general | spot/on-demand | none |
| `memory-optimized` | general | spot/on-demand | none |
| `batch-processing` | batch | spot | none |
| `gpu-standard` | gpu | on-demand | `nvidia.com/gpu:NoSchedule` |
| `gpu-spot` | gpu | spot | `nvidia.com/gpu:NoSchedule`, `karpenter.sh/capacity-type=spot:NoSchedule` |
| `hpc-distributed` | hpc | on-demand | `nvidia.com/gpu:NoSchedule`, `skyhook.io/workload=hpc:NoSchedule` |

## Kyverno Policies

**Moved to**: `platform/base/kyverno/`

See [Kyverno Component Reference](kyverno.md) for:
- EFA environment injection policy
- HPC toleration injection policy
- Policy verification and debugging

## SkyPilot Configurations

### Cluster Template

SkyPilot cluster configuration is generated from eksctl templates in `cluster/`:

```
cluster/
├── eksctl-template.yaml   # EKS cluster template
├── iam-cluster.yaml       # IAM roles CloudFormation
├── Makefile               # Cluster operations
└── README.md              # Cluster documentation
```

## Common Operations

### Updating Karpenter Configuration

```bash
# Edit configuration
vim platform/base/karpenter/nodepools.yaml

# Validate
kubectl apply --dry-run=client -f platform/base/karpenter/nodepools.yaml

# Apply
kubectl apply -f platform/base/karpenter/nodepools.yaml

# Verify
kubectl get nodepools,ec2nodeclasses
```

### Debugging Provisioning Issues

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter

# View pending pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check NodeClaims
kubectl get nodeclaims
```

## Related

- [Kyverno Component Reference](kyverno.md)
- [ADR-002: Kyverno Policies](../adrs/002-kyverno-policies.md)
- [Karpenter Operations Runbook](../runbooks/karpenter-ops.md)
- [Implementation Plan: Karpenter](../design/implementation-plan.md#4-provisioning-karpenter)
