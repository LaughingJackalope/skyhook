# Storage Reference

> TODO: Update with actual mount points and bucket names for your environment.

## Storage Tiers

Skyhook provides three storage tiers optimized for different use cases:

```
┌─────────────────────────────────────────────────────────────┐
│                     Storage Hierarchy                        │
├─────────────────────────────────────────────────────────────┤
│  Fastest    │  /mnt/local-scratch  │  NVMe RAID0 (local)   │
│             │  Ephemeral, TB/s     │  Checkpoints, cache    │
├─────────────────────────────────────────────────────────────┤
│  Fast       │  /mnt/data           │  FSx for Lustre        │
│             │  Shared, 1200 Gbps   │  Training data         │
├─────────────────────────────────────────────────────────────┤
│  Durable    │  s3://bucket/        │  S3 Object Storage     │
│             │  Via MOUNT_CACHED    │  Long-term checkpoints │
└─────────────────────────────────────────────────────────────┘
```

## NVMe Local Scratch

### Mount Point
```
/mnt/local-scratch
```

### Characteristics

| Property | Value |
|----------|-------|
| Type | Instance NVMe drives in RAID0 |
| Capacity | Instance-dependent (up to 30 TB on p5) |
| Performance | Millions of IOPS, GB/s throughput |
| Persistence | **Ephemeral** — lost on instance termination |

### Use Cases

- Fast checkpoint writes (before async S3 upload)
- Temporary data processing
- Model weight caching
- SOCI image cache

### Example

```python
import os

SCRATCH = "/mnt/local-scratch"

# Write checkpoint to fast local storage
torch.save(model.state_dict(), f"{SCRATCH}/checkpoint.pt")
```

## FSx for Lustre

### Mount Point
```
/mnt/data
```

### Characteristics

| Property | Value |
|----------|-------|
| Type | Parallel file system |
| Throughput | Up to 1200 Gbps via EFA |
| Persistence | Shared across nodes, persists across jobs |
| S3 Integration | Lazy-loads from linked S3 bucket |

### Use Cases

- Training datasets (shared across nodes)
- Model weights
- Intermediate outputs
- Shared configuration

### Example

```python
import os

DATA_DIR = "/mnt/data"

# Read training data (lazy-loaded from S3 on first access)
dataset = load_dataset(f"{DATA_DIR}/my-dataset")
```

### Performance Tips

1. **Sequential reads** are fastest — data is striped across OSTs
2. **First access** incurs S3 fetch latency
3. **Small files** have higher metadata overhead

## S3 with MOUNT_CACHED

### Configuration

In your SkyPilot task:

```yaml
file_mounts:
  /checkpoints:
    source: s3://your-bucket/checkpoints
    mode: MOUNT_CACHED
```

### Characteristics

| Property | Value |
|----------|-------|
| Write behavior | Fast local write, async S3 upload |
| Read behavior | Cached locally after first access |
| Persistence | Durable in S3 |

### Use Cases

- Long-term checkpoint storage
- Final model artifacts
- Cross-job state sharing

### Example

```python
CHECKPOINT_DIR = "/checkpoints"

def save_checkpoint(model, epoch):
    # Writes to local cache, uploads to S3 in background
    path = f"{CHECKPOINT_DIR}/epoch_{epoch}.pt"
    torch.save(model.state_dict(), path)
```

## Path Summary

| Path | Storage | Speed | Persistence | Sharing |
|------|---------|-------|-------------|---------|
| `/mnt/local-scratch` | NVMe RAID0 | Fastest | Ephemeral | Single node |
| `/mnt/data` | FSx Lustre | Fast | Job lifetime | Multi-node |
| `/checkpoints` (MOUNT_CACHED) | S3 | Medium | Permanent | Multi-job |

## Best Practices

### 1. Use the Right Tier

```python
# Fast temporary work
temp_file = "/mnt/local-scratch/temp.pt"

# Shared training data
data_path = "/mnt/data/dataset"

# Durable checkpoints
checkpoint = "/checkpoints/model.pt"
```

### 2. Stage Data to Local

For repeated reads, copy to NVMe:

```bash
# In setup
cp /mnt/data/hot-data.tar /mnt/local-scratch/
tar -xf /mnt/local-scratch/hot-data.tar -C /mnt/local-scratch/
```

### 3. Checkpoint Strategy

```python
# Write to NVMe (fast)
local_ckpt = "/mnt/local-scratch/checkpoint.pt"
torch.save(state, local_ckpt)

# Copy to S3 (durable)
import shutil
shutil.copy(local_ckpt, "/checkpoints/checkpoint.pt")
```

## Quotas

TODO: Add actual quota values.

| Storage | Default Quota |
|---------|---------------|
| FSx per tenant | TBD |
| S3 checkpoints | TBD |
| NVMe local | Instance-limited |

## See Also

- [Checkpointing Guide](../guides/checkpointing.md)
- [Capabilities](../platform/capabilities.md)

