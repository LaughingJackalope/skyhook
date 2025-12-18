# Platform Bootstrap

Makefile-driven deployment of EKS platform components. No GitOps controller required—deploy directly from your terminal.

## Quick Start

```bash
# Auto-discover all variables from AWS (kubectl context, IAM roles, SQS queues)
eval $(make env)

# Deploy everything
make deploy
```

That's it. The Makefile auto-discovers:
- **Cluster info** from `kubectl` context and `aws eks describe-cluster`
- **IRSA roles** from IAM by naming convention (`{cluster-name}-{component}`)
- **SQS queues** for Karpenter/NTH by prefix matching

## Architecture

The platform deploys in **9 numbered layers**, each building on the previous:

| Layer | Components | Method |
|-------|------------|--------|
| **00** | Namespaces | `kubectl apply` |
| **01** | EBS, EFS, FSx CSI drivers | `helm install` |
| **02** | VPC CNI, Load Balancer Controller, External DNS | `helm install` |
| **03** | Secrets Store CSI + AWS Provider | `helm install` |
| **04** | Prometheus Stack, Fluent Bit | `helm install` |
| **05** | Kyverno + ClusterPolicies | `helm` + `kubectl` |
| **06** | Karpenter + NodeClasses/Pools | `helm` + `kubectl` |
| **07** | KEDA, Node Termination Handler | `helm` + `kubectl` |
| **08** | DCGM Exporter, K8sGPT | `helm` + `kubectl` |

## Prerequisites

- `kubectl` configured for your EKS cluster
- `helm` v3.x
- AWS credentials with cluster access
- IRSA roles created (see [Environment Variables](#environment-variables))

## Commands

### Environment Discovery

```bash
make env         # Print export statements (pipe to eval)
make env-file    # Write .env file to source later
make env-check   # Show what was discovered with ✅/❌
```

### Full Deployment

```bash
make deploy      # Deploy all layers (00 → 08)
make destroy     # Tear down all layers (08 → 00)
make status      # Show deployment status
make validate    # Validate all kustomize manifests
```

### Layer-by-Layer

```bash
make deploy-00   # Namespaces only
make deploy-01   # Storage drivers only
make deploy-02   # Networking only
# ... etc

make destroy-05  # Remove policy layer only
```

### Individual Components

```bash
make deploy-01-ebs        # Just EBS CSI
make deploy-02-lb         # Just Load Balancer Controller
make deploy-05-kyverno    # Just Kyverno (no policies)
make deploy-05-policies   # Just Kyverno policies
make deploy-06-karpenter  # Just Karpenter helm chart
make deploy-06-resources  # Just NodeClasses/NodePools
```

## Environment Variables

All variables are **auto-discovered** from AWS. Run `make env-check` to see what was found.

### Auto-Discovery Sources

| Variable | Discovered From |
|----------|-----------------|
| `CLUSTER_NAME` | `kubectl config current-context` |
| `AWS_REGION` | `aws configure get region` |
| `CLUSTER_ENDPOINT` | `aws eks describe-cluster` |
| `VPC_ID` | `aws eks describe-cluster` |
| `KARPENTER_QUEUE` | `aws sqs list-queues` (prefix match) |
| `NTH_QUEUE` | `aws sqs list-queues` (prefix match) |
| `*_ROLE_ARN` | `aws iam get-role` (naming convention) |

### IRSA Role Naming Convention

The Makefile looks for IAM roles named `{cluster-name}-{component}`:

| Component | Expected Role Name |
|-----------|-------------------|
| EBS CSI | `{cluster}-ebs-csi` |
| EFS CSI | `{cluster}-efs-csi` |
| FSx CSI | `{cluster}-fsx-csi` |
| Load Balancer | `{cluster}-aws-load-balancer-controller` |
| External DNS | `{cluster}-external-dns` |
| Fluent Bit | `{cluster}-fluent-bit` |
| Karpenter | `{cluster}-karpenter` |
| KEDA | `{cluster}-keda` |
| NTH | `{cluster}-aws-node-termination-handler` |
| K8sGPT | `{cluster}-k8sgpt` |

### Manual Override

Any variable can be overridden:

```bash
# Override a single variable
CLUSTER_NAME=my-cluster make deploy

# Or export before running
export KARPENTER_QUEUE="https://sqs.us-west-2.amazonaws.com/123456789012/my-queue"
make deploy
```

## Directory Structure

```
platform/
├── Makefile                    # Deployment orchestration
├── README.md                   # This file
│
├── 00-namespaces/              # Layer 00: Core namespaces
│   ├── namespaces.yaml
│   └── kustomization.yaml
│
├── 01-storage/                 # Layer 01: Storage drivers
│   ├── ebs-csi-values.yaml
│   ├── efs-csi-values.yaml
│   └── fsx-csi-values.yaml
│
├── 02-networking/              # Layer 02: Network components
│   ├── vpc-cni-values.yaml
│   ├── lb-controller-values.yaml
│   └── external-dns-values.yaml
│
├── 03-secrets/                 # Layer 03: Secrets management
│   ├── secrets-store-csi-values.yaml
│   └── secrets-store-provider-aws-values.yaml
│
├── 04-observability/           # Layer 04: Monitoring & logging
│   ├── prometheus-stack-values.yaml
│   └── fluent-bit-values.yaml
│
├── 05-policy/                  # Layer 05: Policy engine
│   ├── kyverno-values.yaml
│   └── policies/               # ClusterPolicies (kubectl apply)
│       ├── inject-efa-env.yaml
│       └── inject-hpc-tolerations.yaml
│
├── 06-karpenter/               # Layer 06: Autoscaling
│   ├── karpenter-values.yaml
│   └── manifests/              # NodeClasses & NodePools
│       ├── ec2nodeclasses.yaml
│       └── nodepools.yaml
│
├── 07-scaling/                 # Layer 07: Event-driven scaling
│   ├── keda-values.yaml
│   ├── nth-values.yaml
│   └── manifests/              # TriggerAuthentication
│       └── trigger-auth-aws.yaml
│
└── 08-apps/                    # Layer 08: Platform apps
    ├── dcgm-exporter-values.yaml
    ├── k8sgpt-operator-values.yaml
    └── manifests/              # K8sGPT CR, RBAC, Ingress
        ├── k8sgpt-cr.yaml
        ├── k8sgpt-rbac.yaml
        └── k8sgpt-ingress.yaml
```

## Customization

### Override Helm Values

Each `*-values.yaml` file contains sensible defaults. Override at deploy time:

```bash
helm upgrade --install kyverno kyverno/kyverno \
  --namespace kyverno \
  --values 05-policy/kyverno-values.yaml \
  --set admissionController.replicas=5  # Override
```

### Cluster-Specific Overlays

For multi-cluster deployments, create a `values/` directory:

```
platform/
└── values/
    ├── dev.yaml
    ├── staging.yaml
    └── prod.yaml
```

Then deploy with:

```bash
helm upgrade --install ... \
  --values 05-policy/kyverno-values.yaml \
  --values values/prod.yaml
```

## Troubleshooting

### Helm Release Stuck

```bash
# Check release status
helm status <release-name> -n <namespace>

# Force uninstall and retry
helm uninstall <release-name> -n <namespace> --no-hooks
make deploy-XX
```

### CRD Not Found

Some layers apply CRDs via Helm, then custom resources via kubectl. If you see "resource not found":

```bash
# Wait for CRDs to be established
kubectl wait --for=condition=established crd/nodepools.karpenter.sh --timeout=60s

# Retry the kubectl apply
kubectl apply -k 06-karpenter/manifests/
```

### Karpenter NodePool Not Provisioning

```bash
# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f

# Verify EC2NodeClass
kubectl get ec2nodeclasses
kubectl describe ec2nodeclass default
```

### Prometheus Stack Timeout

The Prometheus stack is large and may timeout on first install:

```bash
# Increase timeout
helm upgrade --install kube-prometheus-stack prometheus/kube-prometheus-stack \
  --namespace observability \
  --values 04-observability/prometheus-stack-values.yaml \
  --wait --timeout 15m
```

## Post-Bootstrap: Flux for Tenants

After platform bootstrap, researchers can optionally use Flux for their own workloads:

```bash
# Researcher bootstraps Flux in their namespace
flux bootstrap github \
  --owner=my-org \
  --repository=my-workloads \
  --path=clusters/skyhook-accel-usw2-v42 \
  --personal
```

This keeps platform infra Makefile-driven while enabling GitOps for tenant workloads.

## Version Reference

| Component | Chart Version |
|-----------|---------------|
| VPC CNI | 1.18.2 |
| EBS CSI | 2.32.0 |
| EFS CSI | 2.5.5 |
| FSx CSI | 1.6.1 |
| Secrets Store CSI | 1.4.5 |
| AWS Secrets Provider | 0.3.9 |
| Load Balancer Controller | 1.9.2 |
| External DNS | 1.15.0 |
| Prometheus Stack | 61.2.0 |
| Fluent Bit | 0.46.6 |
| Kyverno | 3.2.7 |
| Karpenter | 1.2.0 |
| KEDA | 2.14.0 |
| Node Termination Handler | 0.21.0 |
| DCGM Exporter | 3.4.2 |
| K8sGPT Operator | 0.2.3 |

