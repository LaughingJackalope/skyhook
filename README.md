# Skyhook

**High-Performance Compute-as-a-Service for ML Research**

Skyhook is the Acceleration team's platform for providing researchers with frictionless access to GPU compute. Built on Amazon EKS with [SkyPilot](https://skypilot.readthedocs.io/) as the primary interface, Skyhook handles the complexity of provisioning, networking, and storage so researchers can focus on their work.

## What Skyhook Provides

| Feature | Benefit |
|---------|---------|
| **Fast GPU provisioning** | Nodes ready in minutes via Karpenter |
| **Optimized networking** | EFA automatically configured for multi-node training |
| **High-performance storage** | FSx for Lustre with automatic NVMe caching |
| **Instant container startup** | SOCI lazy-loading for large ML images |
| **Spot resilience** | Automatic checkpointing and recovery on preemption |
| **Task-based logging** | Find logs by job ID, not pod name |

## Quick Start

### For Researchers

1. Install SkyPilot: `pip install skypilot`
2. Configure access to the cluster (contact Acceleration team)
3. Submit your first job:

```yaml
# hello-gpu.yaml
name: hello-gpu
resources:
  accelerators: A100:1
run: |
  python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

```bash
sky launch hello-gpu.yaml
```

See the [Quick Start Guide](docs/guides/quick-start.md) for detailed instructions.

### For Platform Operators

1. **Create foundation** (VPC, FSx, placement groups):
   ```bash
   cd foundation/
   make foundation-up ENV=accel-usw2
   ```

2. **Create cluster release**:
   ```bash
   cd cluster/
   make cluster-up ENV=accel-usw2 CLUSTER=v42
   ```

3. Flux automatically reconciles platform components after cluster creation.

See [architecture.md](architecture.md), [foundation/README.md](foundation/README.md), and [cluster/README.md](cluster/README.md).

## Documentation

| Section | Audience | Description |
|---------|----------|-------------|
| [Platform Overview](docs/platform/overview.md) | Researchers | What Skyhook is and how it helps |
| [Capabilities](docs/platform/capabilities.md) | Researchers | Available GPUs, storage, networking |
| [Guides](docs/guides/) | Researchers | Quick start, checkpointing, multi-node, debugging |
| [Reference](docs/reference/) | Researchers | Instance types, storage paths, environment variables |
| [Internal Docs](docs/internal/) | Operators | Design docs, runbooks, ADRs, component reference |

### Build Documentation Locally

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

Then open http://localhost:8000

## Repository Structure

```
├── foundation/         # Layer 0: Long-lived infrastructure (VPC, FSx, placement groups)
│   ├── templates/      # CloudFormation templates
│   └── params/         # Environment parameters
├── cluster/            # Layer 1: Per-release EKS clusters
│   ├── eksctl-template.yaml
│   └── iam-cluster.yaml
├── platform/           # Layer 2: GitOps-managed services (Karpenter, NTH, observability)
│   └── base/
├── skypilot-infra/     # Karpenter NodePools + Kyverno policies
├── docs/               # Documentation (MkDocs)
├── control/            # Control plane (quotas, RBAC, scheduling)
├── workloads/          # Workload templates and overlays
├── infra/              # (deprecated) Legacy infrastructure
└── policies/           # Guard/OPA policies
```

See [architecture.md](architecture.md) for detailed architecture documentation.

## Key Technologies

- **[SkyPilot](https://skypilot.readthedocs.io/)** — Researcher interface for job submission
- **[Karpenter](https://karpenter.sh/)** — Just-in-time node provisioning
- **[Kyverno](https://kyverno.io/)** — Policy-based configuration automation
- **[Flux](https://fluxcd.io/)** — GitOps continuous delivery
- **[FSx for Lustre](https://aws.amazon.com/fsx/lustre/)** — High-performance parallel storage
- **[EFA](https://aws.amazon.com/hpc/efa/)** — Elastic Fabric Adapter for low-latency networking
- **[SOCI](https://github.com/awslabs/soci-snapshotter)** — Seekable OCI for lazy image loading

## The Skyhook Contract

| Skyhook Handles | You Handle |
|-----------------|------------|
| Provisioning GPU nodes quickly | Writing valid SkyPilot tasks |
| Configuring EFA for NCCL | Using NCCL (not custom networking) |
| Mounting FSx to `/mnt/data` | Reading/writing to standard paths |
| Preserving state on spot preemption | Implementing SIGTERM handlers |
| Task-based log aggregation | Logging to stdout/stderr |

## Contributing

This repository is maintained by the Acceleration team. For changes:

1. Create a feature branch
2. Make changes and test locally
3. Submit a pull request
4. Changes deploy automatically via Flux after merge

## Support

- **Researchers**: Contact the Acceleration team for platform issues
- **Documentation**: Submit issues or PRs for doc improvements

---

*Skyhook is a researcher experience initiative by the Acceleration team.*

