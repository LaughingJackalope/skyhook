# Checkpointing

> TODO: Add code examples specific to your environment.

Proper checkpointing is essential for long-running jobs, especially on spot instances where preemption can occur with only 2 minutes notice.

## Why Checkpointing Matters

- **Spot instances** can be interrupted at any time
- **Without checkpoints**, you lose all progress since job start
- **With checkpoints**, you lose at most a few minutes of work

## The Skyhook Checkpoint Pattern

### 1. Handle SIGTERM

When a spot instance is being reclaimed, Skyhook sends `SIGTERM` to your process. You have ~2 minutes to save state.

```python
import signal
import sys

def graceful_exit(signum, frame):
    print("Caught SIGTERM. Saving emergency checkpoint...")
    save_checkpoint()  # Your checkpoint function
    sys.exit(0)  # Exit 0 = retriable event

signal.signal(signal.SIGTERM, graceful_exit)
```

!!! warning "Important"
    Many Python scripts ignore SIGTERM by default. You **must** register a handler.

### 2. Use Fast Local Storage

Write checkpoints to NVMe first, then sync to S3:

```python
import os

LOCAL_SCRATCH = "/mnt/local-scratch"
CHECKPOINT_DIR = os.path.join(LOCAL_SCRATCH, "checkpoints")

def save_checkpoint(model, optimizer, epoch):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    checkpoint_path = os.path.join(CHECKPOINT_DIR, f"checkpoint_{epoch}.pt")
    
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, checkpoint_path)
    
    # Async upload to S3 happens automatically with MOUNT_CACHED
    print(f"Checkpoint saved to {checkpoint_path}")
```

### 3. Use MOUNT_CACHED for S3

In your SkyPilot task file:

```yaml
file_mounts:
  /checkpoints:
    source: s3://your-bucket/checkpoints
    mode: MOUNT_CACHED  # Fast local writes, async S3 upload
```

## Checkpoint Frequency

| Job Duration | Recommended Frequency |
|--------------|----------------------|
| < 1 hour | Every 15 minutes |
| 1-8 hours | Every 30 minutes |
| > 8 hours | Every hour |

## Recovery Flow

When a job is preempted and rescheduled:

1. Skyhook provisions a new node
2. Your S3 checkpoint mount is available
3. Your code should check for existing checkpoints:

```python
def load_latest_checkpoint(model, optimizer):
    checkpoints = sorted(glob.glob("/checkpoints/checkpoint_*.pt"))
    if checkpoints:
        latest = checkpoints[-1]
        checkpoint = torch.load(latest)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return checkpoint['epoch']
    return 0

# In your training script
start_epoch = load_latest_checkpoint(model, optimizer)
for epoch in range(start_epoch, total_epochs):
    train_one_epoch(...)
    save_checkpoint(model, optimizer, epoch)
```

## Framework-Specific Examples

### PyTorch Lightning

TODO: Add Lightning checkpoint callback example.

### Hugging Face Transformers

TODO: Add Trainer checkpoint example.

### JAX/Flax

TODO: Add Orbax checkpoint example.

## Best Practices

1. **Always handle SIGTERM** — Platform preemption is transparent only if you cooperate
2. **Use `/mnt/local-scratch`** — NVMe is orders of magnitude faster than network storage
3. **Checkpoint frequently** — The cost of checkpointing is lower than the cost of lost progress
4. **Test recovery** — Verify your job can resume from a checkpoint before long runs

## See Also

- [Spot Recovery Runbook](../internal/runbooks/spot-recovery.md) (internal)
- [Storage Reference](../reference/storage.md)

