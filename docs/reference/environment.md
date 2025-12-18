# Environment Variables

## Auto-Injected Variables

Skyhook automatically injects environment variables to configure your workload for optimal performance.

### EFA / NCCL Configuration

When you request EFA resources (`vpc.amazonaws.com/efa`), Kyverno injects:

| Variable | Value | Purpose |
|----------|-------|---------|
| `FI_PROVIDER` | `efa` | Use EFA libfabric provider |
| `FI_EFA_USE_DEVICE_RDMA` | `1` | Enable RDMA operations |
| `NCCL_DEBUG` | `INFO` | NCCL logging level |
| `NCCL_PROTO` | `simple` | Optimized NCCL protocol |

!!! info "Automatic Injection"
    You don't need to set these manually. Skyhook's Kyverno policies inject them when EFA is requested.

### SkyPilot Variables

SkyPilot sets these for all jobs:

| Variable | Example | Purpose |
|----------|---------|---------|
| `SKYPILOT_TASK_ID` | `sky-job-abc123` | Unique task identifier |
| `SKYPILOT_CLUSTER_NAME` | `my-cluster` | Cluster name |
| `SKYPILOT_NUM_NODES` | `2` | Total nodes in job |
| `SKYPILOT_NODE_RANK` | `0` | This node's rank (0-indexed) |
| `SKYPILOT_NODE_0_IP` | `10.0.1.100` | Master node IP |

### CUDA Variables

Standard CUDA environment:

| Variable | Typical Value | Purpose |
|----------|---------------|---------|
| `CUDA_VISIBLE_DEVICES` | `0,1,2,3,4,5,6,7` | Available GPUs |
| `CUDA_HOME` | `/usr/local/cuda` | CUDA installation path |

## Checking Your Environment

From within a job:

```bash
# View all Skyhook-related variables
env | grep -E "(FI_|NCCL_|SKYPILOT|CUDA)"
```

Expected output:
```
FI_PROVIDER=efa
FI_EFA_USE_DEVICE_RDMA=1
NCCL_DEBUG=INFO
NCCL_PROTO=simple
SKYPILOT_TASK_ID=sky-job-abc123
SKYPILOT_NUM_NODES=2
SKYPILOT_NODE_RANK=0
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
```

## Overriding Defaults

You can override auto-injected variables in your task file:

```yaml
envs:
  NCCL_DEBUG: WARN  # Less verbose logging
  NCCL_ALGO: Tree   # Different algorithm
```

## Verifying EFA is Active

Check NCCL is using EFA (not TCP):

```python
import os

# EFA should be configured
assert os.environ.get('FI_PROVIDER') == 'efa', "EFA not configured!"

# Run NCCL operation and check logs for "EFA" transport
```

In logs, look for:
```
NCCL INFO Using network AWS Libfabric and target EFA
```

Not:
```
NCCL INFO Using network Socket
```

## Standard Paths

These paths are available in all Skyhook jobs:

| Path | Purpose |
|------|---------|
| `/mnt/local-scratch` | Fast NVMe local storage |
| `/mnt/fsx` | FSx for Lustre shared storage (1.2 TiB) |

### FSx Mount Details

- **DNS**: `fs-06f749f9104b7ec01.fsx.us-west-2.amazonaws.com`
- **Mount Name**: `a2cfrb4v`
- **Type**: PERSISTENT_2 (125 MB/s/TiB throughput)

## Debugging Environment Issues

### Variable Not Set

If an expected variable is missing:

1. Verify you requested the right resources (e.g., EFA)
2. Check Kyverno policy is active (Acceleration team)
3. Manually set as workaround:
   ```yaml
   envs:
     FI_PROVIDER: efa
   ```

### Wrong Value

If a variable has an unexpected value:

1. Your task file `envs:` may be overriding
2. Base image may set conflicting values
3. Check with Acceleration team

## See Also

- [Multi-Node Training](../guides/multi-node.md)
- [Kyverno Policies](../internal/component-reference/skypilot-infra.md)
- [NCCL Documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)

