# Skyhook Cluster Releases

Cluster releases are **ephemeral EKS clusters** built on top of a foundation layer. They can be created, validated, promoted, and destroyed independently.

## Architecture

```
Cluster Release (days/weeks)
├── EKS Control Plane (v1.32)
├── System Node Group (Amazon Linux 2, m5.large)
├── OIDC Provider (Pod Identity)
├── IAM Roles (Karpenter, NTH, Fluent Bit, External DNS)
├── ConfigMaps (cluster-config, karpenter-values)
└── Flux GitOps (platform services)
    └── Data Layer (Trino, Spark, Delta Lake)
```

## Live Cluster (skyhook-accel-usw2-v42)

| Resource | Value |
|----------|-------|
| **Cluster Name** | `skyhook-accel-usw2-v42` |
| **Kubernetes** | v1.32.9-eks |
| **Control Plane** | `https://48030A54B86D4E8602A34C494A1B1A2F.gr7.us-west-2.eks.amazonaws.com` |
| **System Nodes** | 2× m5.large (Amazon Linux 2) |
| **Karpenter** | v1.2.0 |
| **NodePools** | 6 (general, compute, memory, gpu-standard, gpu-spot, hpc) |

## Quick Start

```bash
# 1. Create a cluster release
make cluster-up ENV=accel-usw2 CLUSTER=v42

# 2. Update IAM with OIDC provider
make iam-update ENV=accel-usw2 CLUSTER=v42

# 3. Create cluster ConfigMaps
make cluster-config-update ENV=accel-usw2 CLUSTER=v42

# 4. Bootstrap Flux (this will apply all platform components)
make flux-bootstrap ENV=accel-usw2 CLUSTER=v42

# 5. Check status
make cluster-status ENV=accel-usw2 CLUSTER=v42

# 6. (Later) Promote to production
make cluster-promote ENV=accel-usw2 CLUSTER=v42
```

## Naming Convention

```
Cluster Name: skyhook-{env}-{release}
Example:      skyhook-accel-usw2-v42
              skyhook-accel-usw2-2024-12-06
              skyhook-accel-usw2-canary
```

## Files

| File | Description |
|------|-------------|
| `eksctl-template.yaml` | EKS cluster configuration template |
| `iam-cluster.yaml` | Per-cluster IAM roles (IRSA) |
| `Makefile` | Cluster lifecycle commands |
| `.generated/` | Generated eksctl configs (gitignored) |

## ConfigMaps

The cluster creates two ConfigMaps in `flux-system` namespace for Karpenter and other components:

### cluster-config

Contains environment variables for Flux Kustomize substitution:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-config
  namespace: flux-system
data:
  CLUSTER_NAME: skyhook-accel-usw2-v42
  CLUSTER_ENDPOINT: https://48030A54B86D4E8602A34C494A1B1A2F.gr7.us-west-2.eks.amazonaws.com
  ENVIRONMENT: accel-usw2
  ACCOUNT_ID: "751442549699"
  REGION: us-west-2
  FSX_DNS_NAME: fs-06f749f9104b7ec01.fsx.us-west-2.amazonaws.com
  FSX_MOUNT_NAME: a2cfrb4v
  HPC_SUBNET_IDS: subnet-0aafb87c85d8aca7a,subnet-05c02e2645ba8cbb6
  PLACEMENT_GROUPS: skyhook-accel-usw2-cpg-us-west-2a-alpha,...
```

### karpenter-values

Contains Helm values for Karpenter (used via `valuesFrom`):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: karpenter-values
  namespace: flux-system
data:
  values.yaml: |
    settings:
      clusterName: skyhook-accel-usw2-v42
      clusterEndpoint: https://...
    serviceAccount:
      create: true
      name: karpenter
      annotations:
        eks.amazonaws.com/role-arn: arn:aws:iam::751442549699:role/skyhook-accel-usw2-v42-karpenter
```

## Karpenter Tagging Requirements

For Karpenter to discover resources, specific tags must be set:

### Security Group Tag

The cluster security group must have:

```
karpenter.sh/discovery: skyhook-accel-usw2-v42
```

This is set automatically by `make cluster-up`, but can be added manually:

```bash
aws ec2 create-tags --resources sg-XXXXX \
  --tags Key=karpenter.sh/discovery,Value=skyhook-accel-usw2-v42
```

### Subnet Tags

Foundation subnets are tagged by role (set by foundation stack):

```
skyhook.io/subnet-role: system  # or 'hpc'
```

Karpenter EC2NodeClasses use these tags to discover subnets.

## IAM Roles

The IAM stack creates per-cluster IRSA roles:

| Role | Service Account | Purpose |
|------|-----------------|---------|
| `{cluster}-karpenter` | `karpenter:karpenter` | Node provisioning |
| `{cluster}-nth` | `kube-system:aws-node-termination-handler` | Spot handling |
| `{cluster}-fluent-bit` | `logging:fluent-bit` | Log shipping |
| `{cluster}-external-dns` | `external-dns:external-dns` | DNS management |
| `{cluster}-karpenter-node` | EC2 instances | Node instance profile |

### IAM Stack Outputs

| Output | Description | Example |
|--------|-------------|---------|
| `KarpenterControllerRoleArn` | Karpenter IRSA role | `arn:aws:iam::751442549699:role/skyhook-accel-usw2-v42-karpenter` |
| `KarpenterNodeRoleArn` | Node instance role | `arn:aws:iam::751442549699:role/skyhook-accel-usw2-v42-karpenter-node` |
| `KarpenterNodeInstanceProfileName` | Instance profile | `skyhook-accel-usw2-v42-karpenter-node` |

### Updating IAM After Cluster Creation

```bash
make iam-update ENV=accel-usw2 CLUSTER=v42
```

This updates the IAM roles with the OIDC provider ID from the created cluster.

## Prerequisites

Before creating a cluster:

1. **Foundation must exist**: `make foundation-status ENV=accel-usw2`
2. **AWS credentials**: Must have EKS, IAM, EC2 permissions
3. **eksctl installed**: `brew install eksctl` or equivalent
4. **kubectl installed**: For Flux bootstrap
5. **Flux CLI**: `brew install fluxcd/tap/flux`

## Lifecycle

### Creating a New Release

```bash
make cluster-up ENV=accel-usw2 CLUSTER=v43
```

This will:
1. Fetch foundation parameters from SSM
2. Generate eksctl config from template
3. Deploy IAM stack (creates roles before cluster)
4. Create EKS cluster (references foundation VPC)
5. Create cluster-config ConfigMaps

### Post-Creation Steps

```bash
# 1. Update IAM with OIDC provider
make iam-update ENV=accel-usw2 CLUSTER=v43

# 2. Bootstrap Flux (this will apply all platform components)
make flux-bootstrap ENV=accel-usw2 CLUSTER=v43

# 3. Verify core Flux Kustomizations
kubectl get kustomizations -n flux-system

# 4. Verify platform components
kubectl get nodepools,ec2nodeclasses
```

### Validating

After creation, verify:

```bash
# Check nodes
kubectl get nodes --context skyhook-accel-usw2-v43

# Check Karpenter
kubectl get nodepools,ec2nodeclasses

# Check all HelmReleases
kubectl get helmreleases -n flux-system
```

### Promoting

When ready to make a release active:

```bash
make cluster-promote ENV=accel-usw2 CLUSTER=v43
```

This updates SSM parameter `/skyhook/accel-usw2/active-cluster` for discovery.

### Deleting

```bash
make cluster-down ENV=accel-usw2 CLUSTER=v42
```

This will:
1. Drain Karpenter-managed nodes (deletes NodePools)
2. Delete EKS cluster
3. Delete IAM stack

## Blue-Green Deployments

Run two clusters simultaneously for zero-downtime upgrades:

```bash
# Current production
skyhook-accel-usw2-v42  (active)

# New release
make cluster-up ENV=accel-usw2 CLUSTER=v43

# Validate v43
# ... run tests ...

# Promote v43
make cluster-promote ENV=accel-usw2 CLUSTER=v43

# Drain users from v42
# ... notify users ...

# Delete v42
make cluster-down ENV=accel-usw2 CLUSTER=v42
```

## Troubleshooting

### Cluster Creation Fails

1. Check foundation exists: `make foundation-status ENV=accel-usw2`
2. Check AWS credentials: `aws sts get-caller-identity`
3. Check CloudFormation events for IAM stack
4. Check eksctl logs

### Karpenter Not Ready

```bash
# Check EC2NodeClass status
kubectl describe ec2nodeclass default

# Common issues:
# - SecurityGroupsNotFound: Add karpenter.sh/discovery tag
# - SubnetsNotFound: Check skyhook.io/subnet-role tags
# - InstanceProfileNotFound: Run make iam-update

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter
```

### ConfigMap Missing

```bash
# Recreate ConfigMaps
make cluster-config-update ENV=accel-usw2 CLUSTER=v42
```

### IAM Role Not Working

```bash
# Verify OIDC provider exists
aws eks describe-cluster --name skyhook-accel-usw2-v42 \
  --query 'cluster.identity.oidc.issuer'

# Update IAM stack
make iam-update ENV=accel-usw2 CLUSTER=v42

# Restart Karpenter to pick up new credentials
kubectl rollout restart deployment karpenter -n karpenter
```

## Relationship to Foundation

Clusters depend on foundation resources:

| Foundation Resource | How Cluster Uses It |
|---------------------|---------------------|
| VPC ID | eksctl `vpc.id` |
| System Subnets | EKS control plane + system nodes |
| HPC Subnets | Karpenter GPU node provisioning |
| FSx | ConfigMap values for user-data |
| Placement Groups | Karpenter EC2NodeClass (future) |
| KMS Key | EBS volume encryption |

## Multiple Clusters

A single foundation can host multiple clusters:

```
Foundation: accel-usw2
├── skyhook-accel-usw2-v42    (production)
├── skyhook-accel-usw2-v43    (canary testing)
├── skyhook-accel-usw2-alice  (researcher experiment)
└── skyhook-accel-usw2-perf   (performance testing)
```

All share:
- Same VPC (network isolation via security groups)
- Same FSx (data sharing, separate scratch dirs)
- Same placement groups (EFA capacity)

## Client Discovery

Clients should discover the active cluster via SSM:

```bash
# Query SSM to get the active cluster
aws ssm get-parameter \
  --name "/skyhook/accel-usw2/active-cluster" \
  --query "Parameter.Value" --output text

# Example output: skyhook-accel-usw2-v42
```

This allows zero-downtime cluster upgrades.
