# ADR-003: SOCI for Container Image Loading

## Status

Accepted

## Context

Deep learning container images are large—typically 15GB+ for full PyTorch/TensorFlow installations with CUDA. On a freshly provisioned Karpenter node, standard image pull takes **5-10 minutes**, during which expensive GPU hardware sits idle.

This latency:
- Destroys the "interactive" feel of the platform
- Reduces cluster efficiency (nodes not productive)
- Frustrates researchers waiting for jobs to start
- Multiplies with scale (100 nodes = 100 pulls)

Options evaluated:

1. **SOCI (Seekable OCI)** — Lazy-loading via FUSE filesystem
2. **Pre-warmed AMIs** — Bake images into custom AMIs
3. **kube-fledged** — Pre-cache images on nodes
4. **Standard pull** — Accept the latency

## Decision

**Use SOCI snapshotter for lazy-loading container images, with NVMe as the local cache.**

Configuration:
- Enable SOCI snapshotter in containerd (Bottlerocket)
- Pre-compute SOCI indices for common ML images
- Store indices in ECR alongside images
- Configure NVMe (`/mnt/local-scratch`) as SOCI cache directory

## Consequences

### Positive

- **50%+ reduction in startup latency**: Pods start in seconds, not minutes
- **Near-instant application start**: Training code runs immediately
- **Flexibility**: Any image version works, not locked to AMI contents
- **Better cluster utilization**: Nodes productive immediately
- **Cache efficiency**: NVMe caching speeds subsequent accesses

### Negative

- **FUSE overhead**: Small latency hit on file operations
- **Index requirement**: Images need pre-computed SOCI index
- **Fallback latency**: Missing index = full pull (worse than baseline)
- **Compatibility**: Requires containerd with SOCI snapshotter support
- **Operational burden**: Need to maintain indexed image list

### Neutral

- Need process to generate indices for new images
- Bottlerocket AMI choice reinforced

## Alternatives Considered

### Alternative A: Pre-warmed AMIs

**Description**: Bake ML dependencies (PyTorch, TensorFlow, CUDA) into custom AMIs.

**Why rejected**:
- **Extremely rigid**: If user needs `pytorch:2.1` but AMI has `2.0`, full pull occurs anyway
- **High operational burden**: Gold image pipelines, constant patching, version sprawl
- **Combinatorial explosion**: Multiple framework versions × CUDA versions × custom additions
- **Defeats Karpenter benefits**: Lock-in to specific AMIs reduces flexibility

**When to use**: Highly controlled environments with fixed image requirements.

### Alternative B: kube-fledged

**Description**: Kubernetes operator that pre-caches images on nodes.

**Why rejected**:
- Requires "warming" nodes that might be deleted by Karpenter
- Doesn't solve initial pull problem on fresh nodes
- Adds operational complexity
- Less effective in dynamic, just-in-time environment

**When to use**: Static node pools where warming is practical.

### Alternative C: Accept Standard Pull Latency

**Description**: Use standard image pull and accept 5-10 minute startup.

**Why rejected**:
- **Fundamentally incompatible with RX goals**
- Destroys platform interactivity
- Wastes GPU compute during idle time
- Frustrates researchers

**When to use**: Never for production ML platforms.

## Implementation Notes

### SOCI Index Generation

Indices must be generated for each image:tag and pushed to ECR:

```bash
# Generate SOCI index
soci create <image>:<tag>

# Push index to ECR
soci push <image>:<tag>
```

TODO: Document CI pipeline for automatic index generation.

### Indexed Images

TODO: Maintain list of pre-indexed images:

| Image | Tag | Indexed | Notes |
|-------|-----|---------|-------|
| pytorch/pytorch | 2.1-cuda12.1-cudnn8-runtime | Yes | |
| nvcr.io/nvidia/pytorch | 23.10-py3 | Yes | |
| ... | | | |

### Fallback Behavior

When SOCI index is missing:
1. Log warning (visible in pod events)
2. Fall back to standard pull
3. Alert platform team to add index

### NVMe Cache Configuration

SOCI uses `/mnt/local-scratch/soci-cache` for block caching:

```toml
# In containerd config
[plugins."io.containerd.snapshotter.v1.soci"]
  root_path = "/mnt/local-scratch/soci-cache"
```

This requires NVMe RAID0 to be mounted before containerd starts.

## References

- [AWS SOCI Documentation](https://github.com/awslabs/soci-snapshotter)
- [Slide Content: SOCI Image Loading](../design/slide-content.md#slide-9-image-vending---soci-lazy-loading)
- [Implementation Plan: Image Vending](../design/implementation-plan.md#5-image-vending-soci)

