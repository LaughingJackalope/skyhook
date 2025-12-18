# Platform Overview

> TODO: This page will describe what Skyhook is and its mission.

## What is Skyhook?

Skyhook is a high-performance compute platform built by the Acceleration team to serve ML researchers. It provides:

- GPU compute on demand via SkyPilot
- Optimized networking for distributed training
- High-performance storage with minimal configuration
- Automatic resilience for spot instance workloads

## Mission

*Taking ownership of the researcher experience.*

The Acceleration team's goal is to minimize infrastructure friction—latency in job startup, complexity in data access, and opacity in failure recovery—while maximizing computational throughput and cost-efficiency.

## How It Works

TODO: Add simplified architecture diagram

```mermaid
graph LR
    R[Researcher] --> SP[SkyPilot]
    SP --> K8S[EKS Cluster]
    K8S --> GPU[GPU Nodes]
```

## Key Components

| Component | Purpose |
|-----------|---------|
| SkyPilot | User interface for job submission |
| Karpenter | Just-in-time node provisioning |
| FSx for Lustre | High-performance shared storage |
| EFA | Low-latency networking for NCCL |
| Kyverno | Automatic configuration injection |

## Next Steps

- [View available capabilities](capabilities.md)
- [Submit your first job](../guides/quick-start.md)

