# Debugging

> TODO: Add specific log locations and tooling for your environment.

How to diagnose and fix common issues on Skyhook.

## Finding Your Logs

Skyhook organizes logs by **task ID**, not pod name.

### Via SkyPilot

```bash
# View logs for a specific job
sky logs <job-name>

# Stream logs in real-time
sky logs -f <job-name>
```

### Via CloudWatch

Logs are streamed to CloudWatch with task-based organization:

```
/skyhook/user-jobs/task-<your-task-id>
```

TODO: Add actual CloudWatch log group paths and access instructions.

## Common Issues

### Job Stuck in "Pending"

**Symptoms**: Job shows pending, not starting

**Diagnosis**:
```bash
sky status  # Check job state
sky queue   # View queue position
```

**Common Causes**:

| Cause | Solution |
|-------|----------|
| Quota exceeded | Wait for other jobs to complete or request increase |
| No capacity | Try different instance type or region |
| Invalid configuration | Check task file syntax |

### Job Failed Immediately

**Symptoms**: Job starts but exits quickly with error

**Diagnosis**:
```bash
sky logs <job-name>  # Check stderr/stdout
```

**Common Causes**:

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| `ModuleNotFoundError` | Missing dependency | Add to `setup:` section |
| `CUDA out of memory` | Model too large | Reduce batch size or request more GPUs |
| `Permission denied` | File access issue | Check mount paths |

### Slow Training

**Symptoms**: Training is much slower than expected

**Diagnosis Checklist**:

1. **Check EFA is active** (multi-node):
   ```bash
   grep -i "efa\|transport" logs
   # Should see "EFA", not "TCP"
   ```

2. **Check GPU utilization**:
   ```bash
   nvidia-smi  # Look for GPU utilization %
   ```

3. **Check I/O wait**:
   ```bash
   iostat -x 1  # High await = storage bottleneck
   ```

**Common Causes**:

| Symptom | Cause | Solution |
|---------|-------|----------|
| Low GPU util, high I/O wait | Storage bottleneck | Use NVMe for hot data |
| NCCL using TCP | EFA not configured | Verify EFA resource request |
| Slow image pull | No SOCI index | Contact team to add index |

### Lost Checkpoint After Preemption

**Symptoms**: Job restarted but didn't resume from checkpoint

**Diagnosis**:
- Did you handle SIGTERM?
- Did checkpoint reach S3 before termination?

```python
# Verify SIGTERM handler is registered
import signal
print(signal.getsignal(signal.SIGTERM))
```

**Solution**: See [Checkpointing Guide](checkpointing.md)

### Container Image Pull Timeout

**Symptoms**: Job stuck in `ContainerCreating` for 5+ minutes

**Causes**:
- Large image without SOCI index
- Network issues to ECR

**Solutions**:
- Request SOCI index for your image
- Use a smaller base image
- Check ECR availability

## Advanced Debugging

### SSH into Running Job

```bash
sky ssh <job-name>
```

Once connected:
```bash
# Check GPU status
nvidia-smi

# Check mounts
df -h
mount | grep -E "(fsx|nvme)"

# Check environment
env | grep -E "(FI_|NCCL_|SKYPILOT)"

# Check network
ip addr  # Look for EFA interfaces
```

### Check Node Health

TODO: Add kubectl commands or internal tooling for node inspection.

### View Platform Logs

For Acceleration team members, see [Internal Runbooks](../internal/runbooks/index.md).

## Getting Help

If you've tried the above and are still stuck:

1. Gather:
   - Job name / task ID
   - Error messages
   - What you've tried

2. Contact the Acceleration team with this information

## See Also

- [Quick Start](quick-start.md) — Basic job submission
- [Checkpointing](checkpointing.md) — State preservation
- [Multi-Node](multi-node.md) — Distributed training issues

