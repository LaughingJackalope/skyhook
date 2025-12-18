# Control Plane Reference

Documentation for the `control/base/` directory containing quotas, scheduling, RBAC, and other control plane configurations.

## Directory Structure

```
control/base/
├── cost/                   # Cost management configuration
│   ├── configmap.yaml
│   └── kustomization.yaml
├── ingress/                # Ingress configuration
│   ├── ingressclass.yaml
│   └── kustomization.yaml
├── notebooks/              # Jupyter notebook configuration
│   ├── configmap.yaml
│   └── kustomization.yaml
├── queue/                  # Job queue configuration
│   ├── configmap.yaml
│   └── kustomization.yaml
├── quotas/                 # Resource quotas
│   ├── kustomization.yaml
│   └── quotas.yaml
├── rbac/                   # RBAC policies
│   ├── kustomization.yaml
│   └── rbac.yaml
├── scheduler/              # Scheduler configuration
│   ├── configmap.yaml
│   └── kustomization.yaml
├── kustomization.yaml      # Root kustomization
└── namespaces.yaml         # Control plane namespaces
```

## Components

### Quotas (`quotas/`)

**Purpose**: Define resource quotas for namespaces/tenants.

**`quotas.yaml`** structure:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
  namespace: <tenant-namespace>
spec:
  hard:
    requests.nvidia.com/gpu: "8"
    limits.nvidia.com/gpu: "8"
    requests.vpc.amazonaws.com/efa: "2"
    requests.cpu: "64"
    requests.memory: "256Gi"
    pods: "20"
```

TODO: Document quota tiers and per-tenant quotas.

**Key Quotas for Skyhook**:
- `nvidia.com/gpu`: GPU allocation per namespace
- `vpc.amazonaws.com/efa`: EFA interface allocation
- `cpu` / `memory`: Standard compute resources
- `pods`: Maximum concurrent pods

### RBAC (`rbac/`)

**Purpose**: Role-Based Access Control for platform operations.

**`rbac.yaml`** contains:
- ClusterRoles for platform administrators
- RoleBindings for tenant access
- ServiceAccounts for platform components

TODO: Document RBAC model and roles.

### Queue (`queue/`)

**Purpose**: Job queue configuration for SkyPilot workloads.

TODO: Document queue configuration.

### Scheduler (`scheduler/`)

**Purpose**: Custom scheduler configuration (if using).

TODO: Document scheduler configuration.

### Cost (`cost/`)

**Purpose**: Cost management and attribution configuration.

TODO: Document cost tracking setup.

### Notebooks (`notebooks/`)

**Purpose**: Jupyter notebook spawner configuration.

TODO: Document notebook configuration.

### Ingress (`ingress/`)

**Purpose**: Ingress class and default ingress configuration.

**`ingressclass.yaml`**:
```yaml
apiVersion: networking.k8s.io/v1
kind: IngressClass
metadata:
  name: alb
  annotations:
    ingressclass.kubernetes.io/is-default-class: "true"
spec:
  controller: ingress.k8s.aws/alb
```

## Kustomization Structure

```yaml
# control/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespaces.yaml
  - quotas/
  - rbac/
  - queue/
  - scheduler/
  - cost/
  - ingress/
  - notebooks/
```

## Common Operations

### Adding a New Tenant Quota

See [Tenant Onboarding Runbook](../runbooks/tenant-onboarding.md) for the full process.

Quick steps:
1. Create quota manifest in `quotas/` or tenant-specific overlay
2. Apply via Flux or direct kubectl

### Modifying RBAC

1. Edit `rbac/rbac.yaml`
2. Test with `kubectl auth can-i` 
3. Commit and reconcile

### Viewing Current Quotas

```bash
# All quotas
kubectl get resourcequotas -A

# Specific namespace
kubectl describe quota -n <namespace>

# Current usage
kubectl get quota -n <namespace> -o yaml
```

## Environment Overlays

Per-environment customization is in `clusters/`:

```
clusters/
├── prod/
│   └── kustomization.yaml    # Production-specific patches
└── staging/
    └── kustomization.yaml    # Staging-specific patches
```

Example overlay:
```yaml
# clusters/staging/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../control/base
patches:
  - path: quota-override.yaml
    target:
      kind: ResourceQuota
```

## Related

- [Limits & Quotas](../../platform/limits.md)
- [Tenant Onboarding](../runbooks/tenant-onboarding.md)
- [Component Reference Index](index.md)

