# Multi-Node Training

> TODO: Add actual examples and verify EFA configuration details.

Distributed training across multiple GPU nodes using NCCL and EFA.

## When to Use Multi-Node

- Model too large for single node (e.g., LLMs)
- Training data parallelism across many GPUs
- Need more than 8 GPUs (single p5/p4d limit)

## How Skyhook Helps

When you request EFA resources, Skyhook automatically:

1. **Provisions nodes in a Cluster Placement Group** — Minimizes network latency
2. **Attaches EFA interfaces** — Enables OS-bypass networking
3. **Injects environment variables** — NCCL uses EFA without manual config

## Basic Multi-Node Task

```yaml
# multi-node.yaml
name: distributed-training

resources:
  accelerators: A100:8
  
num_nodes: 2  # Request 2 nodes

setup: |
  pip install torch

run: |
  # SkyPilot sets up the distributed environment
  torchrun \
    --nnodes=$SKYPILOT_NUM_NODES \
    --nproc_per_node=8 \
    --master_addr=$SKYPILOT_NODE_0_IP \
    --master_port=29500 \
    train.py
```

## Environment Variables

Skyhook automatically injects these when EFA is requested:

| Variable | Value | Purpose |
|----------|-------|---------|
| `FI_PROVIDER` | `efa` | Use EFA provider |
| `FI_EFA_USE_DEVICE_RDMA` | `1` | Enable RDMA |
| `NCCL_DEBUG` | `INFO` | NCCL logging |
| `NCCL_PROTO` | `simple` | Optimized protocol |

SkyPilot also provides:

| Variable | Purpose |
|----------|---------|
| `SKYPILOT_NUM_NODES` | Total node count |
| `SKYPILOT_NODE_RANK` | This node's rank |
| `SKYPILOT_NODE_0_IP` | Master node IP |

## Verifying EFA is Active

Check NCCL logs for EFA transport:

```bash
# Look for "EFA" in NCCL initialization
grep -i "efa\|transport" /path/to/logs
```

Expected output:
```
NCCL INFO Using network AWS Libfabric and target EFA
```

If you see `TCP` instead, EFA is not being used.

## Performance Tips

### 1. Use Cluster Placement Groups

Skyhook pre-provisions placement groups. Ensure your nodes land in the same group for minimal latency.

### 2. Optimize NCCL Settings

For large models:

```bash
export NCCL_ALGO=Ring  # or Tree depending on topology
export NCCL_MIN_NCHANNELS=4
```

### 3. Checkpoint Every Epoch

Multi-node jobs are more likely to experience failures:

```python
if rank == 0:  # Only checkpoint from rank 0
    save_checkpoint(model, optimizer, epoch)
```

## Common Issues

### NCCL Timeout

```
NCCL WARN Timeout waiting for connection
```

**Causes**:
- Nodes not in same placement group
- Security group blocking NCCL ports
- One node failed to start

**Solutions**:
- Retry the job
- Check all nodes are healthy
- Contact Acceleration team

### Falling Back to TCP

If logs show TCP instead of EFA:
- Verify you requested `vpc.amazonaws.com/efa` resource
- Check Kyverno policy is active
- Ensure instance type supports EFA

## Example: PyTorch DDP

```python
import torch
import torch.distributed as dist
import os

def setup_distributed():
    dist.init_process_group(
        backend='nccl',
        init_method='env://',
        world_size=int(os.environ['WORLD_SIZE']),
        rank=int(os.environ['RANK'])
    )
    
    local_rank = int(os.environ['LOCAL_RANK'])
    torch.cuda.set_device(local_rank)
    return local_rank

def main():
    local_rank = setup_distributed()
    
    model = YourModel().cuda(local_rank)
    model = torch.nn.parallel.DistributedDataParallel(
        model, 
        device_ids=[local_rank]
    )
    
    # Training loop...
```

## See Also

- [EFA Documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/efa.html)
- [NCCL Documentation](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/)
- [Architecture: EFA Networking](../internal/design/architecture-notes.md)

