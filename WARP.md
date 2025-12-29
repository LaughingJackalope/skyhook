# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Skyhook is a high-performance compute-as-a-service platform for ML research built on Amazon EKS. Researchers interact with the system via SkyPilot; Skyhook handles GPU provisioning (via Karpenter), networking (EFA), and storage (FSx for Lustre + NVMe), while operators manage the underlying AWS infrastructure and Kubernetes platform.

The repository is organized into clear layers:
- `foundation/`: long-lived AWS infrastructure (VPC, FSx, placement groups, endpoints)
- `cluster/`: ephemeral EKS cluster releases built on a foundation
- `platform/`: platform components (CNI, CSI drivers, observability, Kyverno, Karpenter, etc.) deployed onto a cluster
- `control/`, `workloads/`, `policies/`: control-plane configuration, workload templates, and policy definitions
- `docs/`: MkDocs documentation site for both researchers and operators
- `tests/`: Python/pytest-based conformance and validation tests against a live cluster

When modifying behavior, first identify which layer is responsible (foundation, cluster, platform, control, or workloads) and edit the corresponding directory.

## Key Commands

### Root orchestration (`Makefile`)

The root `Makefile` is a façade over the `foundation/`, `cluster/`, and `platform/` Makefiles.

```bash path=null start=null
# End-to-end bring-up of a full stack
make all-up ENV=accel-usw2 CLUSTER=v42

# End-to-end teardown (platform → cluster → foundation)
make all-down ENV=accel-usw2 CLUSTER=v42

# Per-layer entrypoints
make foundation-up ENV=accel-usw2
make cluster-up ENV=accel-usw2 CLUSTER=v42
make platform-up    # Uses current kubectl context

# Root-level docs helpers (uses uv + MkDocs)
make docs-serve     # uv run --group docs mkdocs serve
make docs-build     # uv run --group docs mkdocs build
```

Use the root `Makefile` when you want to coordinate multiple layers; use the per-layer Makefiles (below) when iterating on a specific layer.

### Foundation layer (`foundation/`)

`foundation/Makefile` manages long-lived CloudFormation stacks and their SSM Parameter Store outputs.

```bash path=null start=null
cd foundation/

# Create or update the foundation stack for an environment
make foundation-up ENV=accel-usw2

# Inspect status and CloudFormation outputs
make foundation-status ENV=accel-usw2

# Tear down the foundation (DESTRUCTIVE: deletes FSx and related data)
make foundation-down ENV=accel-usw2

# Lint and validate CloudFormation templates
make lint
make validate ENV=accel-usw2

# Inspect SSM parameters published by the foundation
make ssm-list ENV=accel-usw2
make ssm-get-metadata ENV=accel-usw2
```

Important behavior:
- Templates in `foundation/templates/` are uploaded to an S3 bucket and deployed as nested stacks.
- Foundation outputs (VPC ID, subnet IDs, FSx DNS/mount, placement groups, etc.) are written under `/skyhook/{env}/…` in SSM and are later consumed by `cluster/`.

### Cluster layer (`cluster/`)

`cluster/Makefile` turns a foundation environment into concrete EKS **cluster releases** (immutable clusters with names like `skyhook-accel-usw2-v42`). It generates eksctl configs, deploys an IAM stack, and wires SSM parameters into Flux ConfigMaps.

Typical workflow for a new release:

```bash path=null start=null
cd cluster/

# (Optional) generate eksctl config only
make cluster-config ENV=accel-usw2 CLUSTER=v43

# 1) Create IAM stack + EKS cluster using foundation parameters
make cluster-up ENV=accel-usw2 CLUSTER=v43

# 2) Update IAM with the cluster OIDC provider (IRSA roles completed here)
make iam-update ENV=accel-usw2 CLUSTER=v43

# 3) (Re)generate cluster-config + per-component values ConfigMaps in flux-system
make cluster-config-update ENV=accel-usw2 CLUSTER=v43

# 4) Install Flux controllers and apply platform Kustomizations
make flux-bootstrap ENV=accel-usw2 CLUSTER=v43

# Status, listing, promotion, teardown
make cluster-status  ENV=accel-usw2 CLUSTER=v43
make cluster-list    ENV=accel-usw2
make cluster-promote ENV=accel-usw2 CLUSTER=v43   # updates /skyhook/{env}/active-cluster in SSM
make cluster-down    ENV=accel-usw2 CLUSTER=v42   # deletes EKS + IAM for that release
```

Key mechanics that cross files:
- `_fetch-foundation` reads `/skyhook/{env}/…` SSM parameters written by `foundation/` and injects them into the eksctl template (`eksctl-template.yaml`).
- `_create-cluster-config` builds `flux-system` ConfigMaps (`cluster-config`, `karpenter-values`, `nth-values`, `fluent-bit-values`, storage CSI values, etc.) based on both foundation SSM parameters and per-cluster IAM role ARNs.
- `flux-bootstrap` applies `../clusters/base` Kustomizations so Flux can manage the `platform/` HelmReleases and Kustomizations for that cluster.

### Platform layer (`platform/`)

`platform/` is a Makefile-first bootstrap for platform components (Helm + kubectl), organized into numbered layers `00`–`09`. It auto-discovers cluster and IAM information from AWS and `kubectl`.

```bash path=null start=null
cd platform/

# Discover environment from current kubectl context and AWS APIs
make env         # prints export statements
make env-check   # shows which variables/roles/queues were found
make env-file    # writes a .env file you can source

# Deploy or tear down all layers (00 → 09 or 09 → 00)
make deploy
make destroy

# Check overall platform state
make status      # namespaces, Helm releases, Karpenter NodePools, Kyverno policies
make validate    # kustomize validation of manifests directories

# Layer-/component-specific deployment (useful when iterating)
make deploy-00                 # namespaces
make deploy-01-efs             # EFS CSI only
make deploy-02-lb              # AWS Load Balancer Controller
make deploy-05-kyverno         # Kyverno only
make deploy-05-policies        # Kyverno policies (EFA, HPC tolerations, etc.)
make deploy-06-karpenter       # Karpenter Helm chart
make deploy-06-resources       # Karpenter EC2NodeClasses + NodePools manifests
make deploy-07-nth             # Node Termination Handler
make deploy-08-dcgm            # NVIDIA DCGM exporter

# Docs as a platform workload (built into a container and deployed via Kustomize)
make deploy-09        # build docs image, push to ECR, deploy manifests
make deploy-09-local  # build docs image and deploy without pushing
```

Important behavior and expectations:
- Environment auto-discovery pulls `CLUSTER_NAME`, `AWS_REGION`, `CLUSTER_ENDPOINT`, `VPC_ID`, SQS queues, and IRSA role ARNs from `kubectl` and `aws` CLI.
- IRSA roles follow a strict naming convention `{cluster-name}-{component}` (e.g. `skyhook-accel-usw2-v42-karpenter`), which is assumed throughout the Makefile and in `cluster/_create-cluster-config`.
- The numbered layers implement a dependency chain (namespaces → storage → networking → secrets → observability → policies → Karpenter → scaling → apps → docs). When changing a component, ensure you understand which layer owns it and update the corresponding values files and manifests.

### Tests (`tests/`)

Tests are Python/pytest suites that validate a **live** EKS cluster with the platform installed. They require:
- Python deps from `pyproject.toml` / `tests/requirements.txt` (e.g. `kubernetes`, `pytest`, `pyyaml`).
- A working kubeconfig (the tests call `config.load_kube_config()` and use live cluster APIs).

Common test commands:

```bash path=null start=null
# Run the full conformance and validation suite
pytest tests -v

# Karpenter conformance tests (provisions nodes via NodePools)
pytest tests/test_karpenter.py -v

# Example: run a single Karpenter test
pytest tests/test_karpenter.py::TestKarpenterConformance::test_general_purpose_nodepool -v

# Namespaces, networking, and storage validation against platform manifests
pytest tests/test_namespaces.py -v
pytest tests/test_networking.py -v
pytest tests/test_storage.py -v
```

Behavior to be aware of:
- `test_karpenter.py` creates a temporary namespace (`karpenter-conformance-testing`), deploys pods with `nodeSelector` like `{"skyhook.io/pool": "general-purpose"}`, waits for them to go `Running`, then asserts that the backing node’s labels and instance types match expectations.
- `test_namespaces.py` parses `platform/00-namespaces/namespaces.yaml` and asserts that all declared namespaces exist in the cluster.
- `test_networking.py` and `test_storage.py` verify that key daemonsets/stateful sets (VPC CNI, AWS Load Balancer Controller, External DNS, CSI drivers) are present and running, and that expected StorageClasses defined in `platform/01-storage/ebs-csi-values.yaml` exist.

## High-Level Architecture & Code Structure

### Layered infrastructure model

The system is intentionally decomposed into lifecycle-based layers (documented in `architecture.md` and `docs/internal/design/architecture-notes.md`):
- **Layer 0 – Foundation (`foundation/`)**: long-lived AWS network and storage primitives, deployed via nested CloudFormation stacks. Publishes all derived values (VPC, subnets, FSx, placement groups, etc.) to SSM under `/skyhook/{env}/…`.
- **Layer 1 – Cluster releases (`cluster/`)**: EKS control planes + minimal system node groups, IAM roles, and Flux bootstrap per release (`skyhook-{env}-{release}`). Each release is immutable; new releases are created instead of mutating existing clusters.
- **Layer 2 – Platform services (`platform/`, `clusters/base`, `platform/base`)**: shared services (CNI, CSI drivers, observability, policy engine, Karpenter, scaling, apps) deployed either via the `platform/` Makefile or Flux-managed Kustomizations.
- **Workload layer (`workloads/`, SkyPilot tasks)**: user workloads scheduled on top of Karpenter-provisioned nodes, with behavior shaped by Kyverno policies, quotas, and RBAC.

When reasoning about a change, decide which lifecycle layer it belongs to; do not cross layers unnecessarily (e.g., avoid embedding foundation-specific IDs directly into platform manifests—use SSM + ConfigMaps instead).

### Foundation → Cluster contract (SSM + tagging)

The coupling between foundation and clusters is encoded as a contract:
- Foundation writes SSM parameters like VPC ID, system/HPC subnet IDs, FSx DNS/mount, placement groups, and metadata blobs under `/skyhook/{env}/…`.
- `cluster/_fetch-foundation` reads those parameters to fill the eksctl template and derive AZs and subnets.
- `cluster/_create-cluster-config` stores the same values (plus IAM role ARNs) into `flux-system` ConfigMaps, which Flux uses to template HelmReleases and Kustomizations for platform components.
- AWS resource tags (e.g. `skyhook.io/subnet-role: system|hpc`, `karpenter.sh/discovery: {cluster-name}`) are required for Karpenter EC2NodeClasses to discover subnets and security groups.

Maintaining this contract is critical; if you alter SSM parameter names or tagging conventions, you will need to update both CloudFormation templates and the cluster/platform config generation logic.

### Karpenter NodePool and EC2NodeClass design

Karpenter configuration is split across several locations and tools:
- **Definitions**: `platform/06-karpenter/manifests/ec2nodeclasses.*` and `nodepools.*` (templated via `envsubst` in `platform/Makefile`) describe EC2NodeClasses (`default`, `gpu`, `hpc`) and NodePools (`general-purpose`, `compute-optimized`, `memory-optimized`, `gpu-standard`, `gpu-spot`, `hpc-distributed`).
- **Cluster-scoped values**: `cluster/_create-cluster-config` generates `karpenter-values` and additional ConfigMaps that feed Helm values into the Karpenter chart via Flux or direct Helm deployments.
- **Tests**: `tests/test_karpenter.py` asserts that pods with `skyhook.io/pool` selectors land on nodes with the expected `skyhook.io/tier` and `skyhook.io/pool` labels and appropriate EC2 instance families.

If you change NodePool names, labels, or EC2NodeClass mappings, also update:
- Manifests in `platform/06-karpenter/manifests/`.
- Any Kyverno policies that refer to these labels.
- The Karpenter conformance tests.

### Control plane configuration (`control/`)

Control-plane policies (quotas, RBAC, notebook configuration, ingress, cost, scheduling, queues) live under `control/base/` with environment overlays in `control/clusters/` (documented in `docs/internal/component-reference/control-plane.md`).

Key points:
- `control/base/kustomization.yaml` aggregates namespaces, quotas, RBAC, queue, scheduler, cost, ingress, and notebooks.
- Namespaces/tenants get resource quotas (GPU, EFA, CPU/memory, pods) via `ResourceQuota` manifests under `quotas/`.
- Overlays in `control/clusters/*` adjust these defaults per environment (e.g., staging vs prod) using Kustomize patches.

When changing control-plane behavior, prefer editing the appropriate Kustomize layer instead of inlining overrides elsewhere in the repo.

### Documentation (`docs/`)

The MkDocs site in `docs/` is the canonical user/operator documentation and mirrors the code structure:
- `docs/platform/*`: researcher-facing overview, capabilities, and simplified architecture.
- `docs/guides/*`: how-tos for checkpointing, multi-node jobs, debugging, and quick start.
- `docs/reference/*`: reference pages for environment variables, instance types, and storage.
- `docs/internal/*`: operator-facing design docs, ADRs, component references, and runbooks.

Local docs development is typically done via the root `Makefile` (`make docs-serve` / `make docs-build`) or directly with MkDocs as described in `README.md` and `docs/index.md`.

### CLAUDE.md

`CLAUDE.md` contains a detailed architecture and operations guide targeted at AI coding tools. When making substantial changes to:
- The multi-layer infrastructure model,
- Karpenter NodePools/EC2NodeClasses,
- SSM parameter layout,
- Or the live environment reference,

update both `CLAUDE.md` and this `WARP.md` so they remain consistent about contracts (SSM keys, tags, naming conventions, and major workflows).