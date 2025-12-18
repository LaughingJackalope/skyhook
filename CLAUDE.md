# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skyhook is a high-performance compute-as-a-service platform for ML research built on Amazon EKS. It provides researchers with frictionless access to GPU compute using SkyPilot as the primary interface. The platform handles provisioning, networking, and storage automatically.

## Key Commands

### Foundation Layer (Long-Lived Infrastructure)
```bash
# Create/update foundation (VPC, FSx, placement groups)
cd foundation/
make foundation-up ENV=accel-usw2
make foundation-status ENV=accel-usw2
make foundation-down ENV=accel-usw2  # DESTRUCTIVE: deletes FSx data

# View foundation parameters
make ssm-list ENV=accel-usw2
make ssm-get-metadata ENV=accel-usw2

# Validate CloudFormation templates
make lint      # Run cfn-lint
make validate  # Validate against AWS
```

### Cluster Layer (Ephemeral EKS Releases)
```bash
# Create cluster release
cd cluster/
make cluster-up ENV=accel-usw2 CLUSTER=v42
make iam-update ENV=accel-usw2 CLUSTER=v42  # Update IAM with OIDC after cluster creation
make cluster-config-update ENV=accel-usw2 CLUSTER=v42  # Recreate ConfigMaps

# Manage clusters
make cluster-status ENV=accel-usw2 CLUSTER=v42
make cluster-list ENV=accel-usw2
make cluster-promote ENV=accel-usw2 CLUSTER=v42  # Set as active cluster
make cluster-down ENV=accel-usw2 CLUSTER=v42

# Flux (GitOps)
make flux-bootstrap ENV=accel-usw2 CLUSTER=v42
make flux-status ENV=accel-usw2 CLUSTER=v42
```

### Platform Components
```bash
# Apply platform components (Karpenter, logging, observability, etc.)
kubectl apply -k platform/base/

# Check Karpenter resources
kubectl get nodepools,ec2nodeclasses
kubectl describe ec2nodeclass default

# Check Helm releases
kubectl get helmreleases -n flux-system
```

### Testing
```bash
# Run Karpenter conformance tests
pytest tests/test_karpenter.py -v

# Run single test
pytest tests/test_karpenter.py::TestKarpenterConformance::test_general_purpose_nodepool -v
```

### Documentation
```bash
# Serve documentation locally
pip install -r requirements-docs.txt
mkdocs serve  # http://localhost:8000
```

## Architecture Overview

Skyhook uses a three-layer architecture that separates infrastructure lifecycles:

### Layer 0: Foundation (months/years)
- **Location**: `foundation/` directory
- **Stack Name**: `skyhook-{env}-foundation`
- **Components**: VPC, subnets, FSx for Lustre, placement groups, VPC endpoints, KMS keys
- **Managed By**: CloudFormation (nested stacks in `foundation/templates/`)
- **Parameters**: Stored in SSM under `/skyhook/{env}/`

### Layer 1: Cluster Releases (days/weeks)
- **Location**: `cluster/` directory
- **Naming**: `skyhook-{env}-{release}` (e.g., `skyhook-accel-usw2-v42`)
- **Components**: EKS control plane, system NodeGroup, OIDC provider, IAM roles
- **Managed By**: eksctl (from `eksctl-template.yaml`) + CloudFormation (IAM from `iam-cluster.yaml`)
- **Immutable**: Clusters are releases, not long-lived environments. Create new releases for upgrades.

### Layer 2: Platform Services (hours)
- **Location**: `platform/base/` directory
- **Managed By**: Flux GitOps
- **Components**: Karpenter, Node Termination Handler, Fluent Bit, External DNS, CSI drivers, observability
- **Configuration**: Uses ConfigMaps in `flux-system` namespace for cluster-specific values

### Workload Layer (minutes-hours)
- **Managed By**: Karpenter (just-in-time node provisioning)
- **User Interface**: SkyPilot CLI
- **NodePools**: 6 pools (general-purpose, compute-optimized, memory-optimized, gpu-standard, gpu-spot, hpc-distributed)

## Critical Architecture Patterns

### Cluster Release Model
Clusters are **immutable releases**, not environments. Multiple clusters can run on the same foundation:
- `skyhook-accel-usw2-v42` (production)
- `skyhook-accel-usw2-v43` (canary)
- `skyhook-accel-usw2-exp1` (experiment)

This enables blue-green deployments and zero-downtime upgrades.

### Foundation-to-Cluster Communication
The foundation layer publishes metadata to SSM Parameter Store. Clusters consume these parameters:
- `/skyhook/{env}/vpc-id` - VPC to deploy into
- `/skyhook/{env}/system-subnet-ids` - Subnets for control plane
- `/skyhook/{env}/hpc-subnet-ids` - Subnets for GPU nodes
- `/skyhook/{env}/fsx-dns-name` - FSx mount point
- `/skyhook/{env}/placement-groups` - EFA placement groups

The `cluster/Makefile` targets use `aws ssm get-parameter` to fetch these values during cluster creation.

### Karpenter NodePool Architecture
Three-tier design: NodePools (scheduling policy) → EC2NodeClasses (AWS config) → Actual EC2 instances

**EC2NodeClasses**:
- `default`: General workloads, system subnets, AL2023 AMI
- `gpu`: GPU workloads, HPC subnets, AL2 AMI
- `hpc`: Distributed training, HPC subnets, AL2 AMI + EFA + FSx mount

**NodePools** (with weights for scheduling priority):
- `general-purpose` (weight: 10) → default class
- `compute-optimized` (weight: 20) → default class
- `memory-optimized` (weight: 20) → default class
- `gpu-standard` (weight: 30) → gpu class (on-demand)
- `gpu-spot` (weight: 40) → gpu class (spot)
- `hpc-distributed` (weight: 50) → hpc class (p4d/p5 with EFA)

### Karpenter Resource Discovery
Karpenter discovers AWS resources via tags:

**Security Groups**: Cluster security group must have `karpenter.sh/discovery: {cluster-name}`

**Subnets**: Foundation subnets tagged with `skyhook.io/subnet-role: system` or `hpc`

**Subnet Selection Logic**:
- EC2NodeClasses use `tags` selectors to find subnets
- `default` class selects `skyhook.io/subnet-role: system`
- `gpu` and `hpc` classes select `skyhook.io/subnet-role: hpc`

### ConfigMap-Based Configuration
After cluster creation, ConfigMaps in `flux-system` namespace provide values to Flux/Helm:

**cluster-config**: Simple key-value pairs (CLUSTER_NAME, FSX_DNS_NAME, etc.)

**{component}-values**: YAML Helm values for each service (karpenter-values, fluent-bit-values, etc.)

These are created by `make cluster-up` and regenerated with `make cluster-config-update`.

### IAM and IRSA (IAM Roles for Service Accounts)
Each cluster has its own IAM stack (`iam-cluster.yaml`) that creates:
- Karpenter controller role (IRSA)
- Karpenter node role (instance profile)
- Service-specific roles (NTH, Fluent Bit, External DNS, CSI drivers)

**Two-phase IAM deployment**:
1. `make cluster-up` creates IAM stack without OIDC (some roles incomplete)
2. `make iam-update` updates stack with OIDC provider ID after cluster exists

This is necessary because OIDC provider is created during cluster creation, but Karpenter role must exist before cluster creation.

### FSx Mount Strategy
FSx for Lustre is mounted on HPC nodes via user-data in EC2NodeClass:
- DNS: `{fsx-id}.fsx.{region}.amazonaws.com`
- Mount name: Retrieved from SSM
- Mount point: `/mnt/fsx/`
- NVMe local scratch: `/mnt/local-scratch/` (RAID0 for ephemeral)

## Important Implementation Details

### Generated Files
`.generated/` directories contain templated files. These are gitignored and regenerated during deployment:
- `cluster/.generated/{cluster-name}.yaml` - eksctl config
- `cluster/.generated/*-values.yaml` - Helm values for each service

Always regenerate these rather than editing manually.

### Makefile Parameter Requirements
Foundation and cluster Makefiles require explicit parameters:
- `ENV` - Environment identifier (e.g., `accel-usw2`)
- `CLUSTER` - Cluster release identifier (e.g., `v42`)

These enforce explicit environment naming and prevent accidental operations.

### CloudFormation Template Organization
Foundation uses nested stacks:
- `main.yaml` - Root orchestrator
- `vpc.yaml`, `endpoints.yaml`, `storage.yaml`, `placement-groups.yaml` - Nested stacks

Templates are uploaded to S3 before deployment. The `TemplateBaseUrl` parameter points to S3 bucket.

### Network Topology
VPC CIDR: `10.0.0.0/16` (hard-coded in `accel-usw2`)

Subnet allocation:
- Public: `/24 × 3` (NAT, ALB)
- System: `/22 × 3` (3,072 IPs for control plane + system pods)
- HPC: `/19 × 2` (16,384 IPs for GPU nodes)
- Storage: `/24 × 1` (FSx mount targets)

HPC subnets are large to support high pod density on GPU instances.

### Placement Groups for EFA
Three cluster placement groups ensure physical proximity for RDMA/EFA:
- `skyhook-accel-usw2-cpg-us-west-2a-alpha`
- `skyhook-accel-usw2-cpg-us-west-2a-beta`
- `skyhook-accel-usw2-cpg-us-west-2b-alpha`

These are referenced by name in EC2 launch templates (future Karpenter integration).

### Test Infrastructure
`tests/test_karpenter.py` contains conformance tests that:
1. Create namespace `karpenter-conformance-testing`
2. Deploy test pods with node selectors
3. Wait for Karpenter to provision nodes
4. Validate node labels, taints, instance types
5. Clean up resources

Tests assume a live cluster with Karpenter installed.

## Common Workflows

### Creating a New Cluster Release
```bash
# 1. Ensure foundation exists
cd foundation && make foundation-status ENV=accel-usw2

# 2. Create cluster
cd ../cluster
make cluster-up ENV=accel-usw2 CLUSTER=v43

# 3. Update IAM with OIDC
make iam-update ENV=accel-usw2 CLUSTER=v43

# 4. Install Flux
flux install --context skyhook-accel-usw2-v43

# 5. Apply platform
kubectl apply -k ../platform/base/ --context skyhook-accel-usw2-v43

# 6. Verify Karpenter
kubectl get nodepools,ec2nodeclasses --context skyhook-accel-usw2-v43
```

### Debugging Karpenter Issues
```bash
# Check EC2NodeClass status for errors
kubectl describe ec2nodeclass {name}

# Common errors:
# - "SecurityGroupsNotFound": Add karpenter.sh/discovery tag to cluster SG
# - "SubnetsNotFound": Check skyhook.io/subnet-role tags on foundation subnets
# - "InstanceProfileNotFound": Run make iam-update

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter

# Check NodePool status
kubectl get nodepool -o yaml
```

### Updating Foundation Infrastructure
```bash
# Foundation updates are rare and require careful planning
cd foundation
make foundation-update ENV=accel-usw2

# Safe updates:
# - Adding VPC endpoints
# - Expanding FSx capacity (increase only)
# - Adding placement groups

# Destructive updates (avoid):
# - Changing VPC CIDR
# - Changing subnet allocation
# - Changing FSx deployment type
```

### Blue-Green Cluster Upgrade
```bash
# 1. Create new cluster
make cluster-up ENV=accel-usw2 CLUSTER=v43

# 2. Validate (run tests, check metrics)
pytest tests/test_karpenter.py

# 3. Promote new cluster as active
make cluster-promote ENV=accel-usw2 CLUSTER=v43

# 4. Drain users from old cluster (coordinate with team)

# 5. Delete old cluster
make cluster-down ENV=accel-usw2 CLUSTER=v42
```

## File Structure Conventions

- **CloudFormation templates**: `foundation/templates/*.yaml` (nested stacks)
- **Kubernetes manifests**: `platform/base/{component}/` (Kustomize)
- **Helm releases**: `platform/base/{component}/helmrelease.yaml` (Flux HelmRelease)
- **Karpenter config**: `platform/base/karpenter/nodepools.yaml`, `ec2nodeclasses.yaml`
- **Documentation**: `docs/` (MkDocs site)
- **Tests**: `tests/*.py` (pytest)

## Tagging Strategy

All resources use consistent tags for discovery and organization:

**Foundation resources**:
- `skyhook.io/environment: {env}` - Environment identifier
- `skyhook.io/layer: foundation` - Infrastructure layer
- `skyhook.io/subnet-role: system|hpc|public|storage` - Subnet purpose

**Cluster resources**:
- `skyhook.io/environment: {env}` - Environment identifier
- `skyhook.io/cluster: {cluster-name}` - Cluster identifier
- `karpenter.sh/discovery: {cluster-name}` - Karpenter resource discovery

## Environment-Specific Configuration

Live production environment:
- **Environment**: `accel-usw2`
- **Region**: `us-west-2`
- **VPC**: `vpc-092d808c1bbe46da0`
- **FSx**: `fs-06f749f9104b7ec01`
- **Active Cluster**: `skyhook-accel-usw2-v42`

Parameters are stored in:
- `foundation/params/accel-usw2.json` - Foundation parameters
- SSM Parameter Store - Runtime/shared values
