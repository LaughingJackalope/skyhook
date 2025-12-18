# Welcome to Skyhook

**High-Performance Compute-as-a-Service for ML Research**

Skyhook is the Acceleration team's platform for providing researchers with frictionless access to GPU compute. Built on EKS with SkyPilot as the primary interface, Skyhook handles the complexity of provisioning, networking, and storage so researchers can focus on their work.

## What Skyhook Does For You

- **Fast GPU provisioning** — Nodes ready in minutes, not hours
- **Optimized networking** — EFA automatically configured for multi-node training
- **High-performance storage** — FSx for Lustre with automatic NVMe caching
- **Instant container startup** — SOCI lazy-loading for large ML images
- **Spot resilience** — Automatic checkpointing and recovery on preemption
- **Task-based logging** — Find your logs by job ID, not pod name

## Quick Links

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Submit your first GPU job in 5 minutes

    [:octicons-arrow-right-24: Get started](guides/quick-start.md)

-   :material-server:{ .lg .middle } **Capabilities**

    ---

    See what GPUs, storage, and networking are available

    [:octicons-arrow-right-24: View capabilities](platform/capabilities.md)

-   :material-book-open:{ .lg .middle } **Guides**

    ---

    Best practices for checkpointing, multi-node, and debugging

    [:octicons-arrow-right-24: Read guides](guides/checkpointing.md)

-   :material-tools:{ .lg .middle } **Internal Docs**

    ---

    Acceleration team documentation and runbooks

    [:octicons-arrow-right-24: Internal](internal/index.md)

</div>

## The Skyhook Contract

| Skyhook Handles | You Handle |
|-----------------|------------|
| Provisioning GPU nodes quickly | Writing valid SkyPilot tasks |
| Configuring EFA for NCCL | Using NCCL (not custom networking) |
| Mounting FSx to `/mnt/data` | Reading/writing to standard paths |
| Preserving state on spot preemption | Implementing SIGTERM handlers |
| Task-based log aggregation | Logging to stdout/stderr |

## Getting Help

- **SkyPilot Documentation**: [skypilot.readthedocs.io](https://skypilot.readthedocs.io/)
- **Internal Support**: Contact the Acceleration team

---

*Skyhook is maintained by the Acceleration team.*

