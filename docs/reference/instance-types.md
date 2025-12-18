# Instance Types

Skyhook uses Karpenter to dynamically provision nodes based on workload requirements. Six NodePools are configured to handle different workload types.

## NodePool Overview

| NodePool | Use Case | Instance Families | Capacity | GPU Taint |
|----------|----------|-------------------|----------|-----------|
| `general-purpose` | Web, API, general workloads | m5, m6i, m7i | spot+od | No |
| `compute-optimized` | CPU-intensive processing | c5, c6i, c7i | spot+od | No |
| `memory-optimized` | Caching, large datasets | r5, r6i, r7i | spot+od | No |
| `gpu-standard` | Production GPU training | g5, g6, p4d, p5 | on-demand | Yes |
| `gpu-spot` | GPU experimentation | g5, g4dn | spot | Yes |
| `hpc-distributed` | Multi-node distributed training | p4d, p5 | on-demand | Yes |

## GPU Instances

### NVIDIA H100 (p5 family)

| Instance | GPUs | GPU Memory | vCPUs | RAM | EFA | NVMe |
|----------|------|------------|-------|-----|-----|------|
| p5.48xlarge | 8x H100 | 640 GB HBM3 | 192 | 2 TB | 32x 400 Gbps | 8x 3.84 TB |

**NodePool**: `hpc-distributed` (on-demand only)  
**Best for**: Large language models, cutting-edge research, distributed training

### NVIDIA A100 (p4 family)

| Instance | GPUs | GPU Memory | vCPUs | RAM | EFA | NVMe |
|----------|------|------------|-------|-----|-----|------|
| p4d.24xlarge | 8x A100 40GB | 320 GB HBM2e | 96 | 1.1 TB | 4x 400 Gbps | 8x 1 TB |
| p4de.24xlarge | 8x A100 80GB | 640 GB HBM2e | 96 | 1.1 TB | 4x 400 Gbps | 8x 1 TB |

**NodePool**: `gpu-standard` (on-demand), `hpc-distributed` (on-demand)  
**Best for**: Most deep learning workloads, good balance of performance/availability

### NVIDIA A10G (g5 family)

| Instance | GPUs | GPU Memory | vCPUs | RAM |
|----------|------|------------|-------|-----|
| g5.xlarge | 1x A10G | 24 GB | 4 | 16 GB |
| g5.2xlarge | 1x A10G | 24 GB | 8 | 32 GB |
| g5.4xlarge | 1x A10G | 24 GB | 16 | 64 GB |
| g5.8xlarge | 1x A10G | 24 GB | 32 | 128 GB |
| g5.12xlarge | 4x A10G | 96 GB | 48 | 192 GB |
| g5.24xlarge | 4x A10G | 96 GB | 96 | 384 GB |
| g5.48xlarge | 8x A10G | 192 GB | 192 | 768 GB |

**NodePool**: `gpu-standard` (on-demand), `gpu-spot` (spot)  
**Best for**: Inference, smaller training jobs, experimentation

### NVIDIA T4 (g4dn family) - Spot Only

| Instance | GPUs | GPU Memory | vCPUs | RAM |
|----------|------|------------|-------|-----|
| g4dn.xlarge | 1x T4 | 16 GB | 4 | 16 GB |
| g4dn.2xlarge | 1x T4 | 16 GB | 8 | 32 GB |
| g4dn.4xlarge | 1x T4 | 16 GB | 16 | 64 GB |
| g4dn.8xlarge | 1x T4 | 16 GB | 32 | 128 GB |
| g4dn.12xlarge | 4x T4 | 64 GB | 48 | 192 GB |

**NodePool**: `gpu-spot` (spot only)  
**Best for**: Cost-effective inference, light training, experimentation

## General Purpose Instances

### M-Series (Balanced)

Available sizes: `large`, `xlarge`, `2xlarge`, `4xlarge`

| Family | vCPU/Memory Ratio | Use Case |
|--------|-------------------|----------|
| m5 | 1:4 | General workloads |
| m6i | 1:4 | Newer gen, better price/perf |
| m7i | 1:4 | Latest gen Intel |

**NodePool**: `general-purpose`

### C-Series (Compute Optimized)

Available sizes: `large`, `xlarge`, `2xlarge`, `4xlarge`

| Family | vCPU/Memory Ratio | Use Case |
|--------|-------------------|----------|
| c5 | 1:2 | CPU-bound workloads |
| c6i | 1:2 | Higher single-thread performance |
| c7i | 1:2 | Latest gen Intel |

**NodePool**: `compute-optimized`

### R-Series (Memory Optimized)

Available sizes: `large`, `xlarge`, `2xlarge`, `4xlarge`

| Family | vCPU/Memory Ratio | Use Case |
|--------|-------------------|----------|
| r5 | 1:8 | In-memory caching |
| r6i | 1:8 | Large dataset processing |
| r7i | 1:8 | Latest gen Intel |

**NodePool**: `memory-optimized`

## Requesting Instances in SkyPilot

### Request Specific GPU Type

```yaml
resources:
  accelerators: H100:8  # Request specific GPU type
  # or
  accelerators: A100:4  # Fewer GPUs
  # or
  instance_type: p5.48xlarge  # Exact instance
```

### Force On-Demand (Critical Jobs)

```yaml
resources:
  accelerators: A100:8
  use_spot: false  # Forces gpu-standard pool
```

### Use Spot for Experimentation

```yaml
resources:
  accelerators: A10G:1
  use_spot: true  # Uses gpu-spot pool (cheaper, may be interrupted)
```

## Spot vs On-Demand

| Type | Cost | Availability | Interruption | NodePools |
|------|------|--------------|--------------|-----------|
| Spot | ~70% discount | Variable | Yes (2 min warning) | general-purpose, compute-optimized, memory-optimized, gpu-spot |
| On-Demand | Full price | Guaranteed | No | gpu-standard, hpc-distributed |

!!! warning "Spot Interruption"
    Spot instances can be terminated with 2 minutes notice. Use checkpointing for long-running jobs.

## EFA Support by Instance

| Instance Family | EFA Interfaces | Bandwidth per Interface | NodePool |
|-----------------|----------------|------------------------|----------|
| p5 | 32 | 400 Gbps | hpc-distributed |
| p4d/p4de | 4 | 400 Gbps | hpc-distributed |
| g5.48xlarge | 1 | 100 Gbps | gpu-standard |

!!! info "EFA for Multi-Node Training"
    For efficient multi-node training with NCCL, use the `hpc-distributed` NodePool which provisions EFA-enabled instances in placement groups.

## GPU Memory Guidelines

| Use Case | Recommended GPU | Memory |
|----------|-----------------|--------|
| LLM training (7B+) | H100 or A100 80GB | 80-640 GB |
| Vision models | A100 40GB or A10G | 24-40 GB |
| Small experiments | T4 or A10G | 16-24 GB |
| Inference | A10G or T4 | 16-24 GB |

## Node Taints

GPU nodes are tainted to prevent non-GPU workloads from scheduling on them:

| NodePool | Taints |
|----------|--------|
| gpu-standard | `nvidia.com/gpu:NoSchedule` |
| gpu-spot | `nvidia.com/gpu:NoSchedule`, `karpenter.sh/capacity-type=spot:NoSchedule` |
| hpc-distributed | `nvidia.com/gpu:NoSchedule`, `skyhook.io/workload=hpc:NoSchedule` |

Your workload must tolerate these taints to schedule on GPU nodes. SkyPilot handles this automatically when you request GPU resources.

## See Also

- [Capabilities Overview](../platform/capabilities.md)
- [Storage Reference](storage.md)
- [Architecture](../../architecture.md)
- [AWS Instance Documentation](https://aws.amazon.com/ec2/instance-types/)
