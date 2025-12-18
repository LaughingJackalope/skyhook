# Spot Recovery Runbook

## Overview

This runbook covers recovery procedures when spot instances are interrupted and jobs don't automatically recover as expected.

## Symptoms

- Job shows as "crashed" in SkyPilot instead of "preempted"
- Checkpoint not found after reschedule
- Job stuck in pending after spot interruption
- Logs show SIGKILL instead of graceful SIGTERM handling

## Impact

- **Researcher impact**: Lost training progress, delayed experiments
- **Platform impact**: Wasted compute hours, reduced trust in spot reliability

## Prerequisites

- kubectl access to the cluster
- CloudWatch Logs access
- AWS Console access (for EC2 events)

## Diagnosis

### 1. Check Spot Interruption Events

```bash
# View recent node terminations
kubectl get events --field-selector reason=NodeTermination -A

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter --tail=100
```

### 2. Verify Node Termination Handler

```bash
# Check NTH is running
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-node-termination-handler

# View NTH logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-node-termination-handler --tail=100
```

### 3. Check Checkpoint Status

```bash
# Verify S3 checkpoint bucket
aws s3 ls s3://<checkpoint-bucket>/<task-id>/

# Check if MOUNT_CACHED synced
# Look for async upload completion in logs
```

### 4. Examine Job Logs

```bash
# Get logs from CloudWatch
# Log group: /skypilot/user-jobs/task-<task-id>

# Check for SIGTERM handling
grep -i "sigterm\|checkpoint\|saving" <logs>
```

## Recovery Procedures

### Procedure A: Job Not Rescheduling

**Cause**: SkyPilot doesn't recognize preemption

1. Check exit code of terminated pod:
   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   ```

2. If exit code is non-zero (not 0), the job was treated as a crash

3. Manually reschedule:
   ```bash
   sky launch --cluster <cluster> <task.yaml>
   ```

4. Document the issue for future SIGTERM handler improvements

### Procedure B: Checkpoint Not Found

**Cause**: Checkpoint didn't sync to S3 before termination

1. Check if local checkpoint existed:
   ```bash
   # Review logs for checkpoint write confirmation
   ```

2. Check MOUNT_CACHED sync status:
   ```bash
   # Look for sync completion in Fluent Bit logs
   ```

3. If checkpoint was lost:
   - Restart job from last known good checkpoint
   - Review checkpoint frequency with researcher

### Procedure C: New Node Fails to Provision

**Cause**: Capacity exhausted in current AZ/instance type

1. Check Karpenter provisioning:
   ```bash
   kubectl describe nodepools
   kubectl get events -n karpenter
   ```

2. If capacity issue, consider:
   - Different AZ
   - Different instance type
   - On-demand fallback

3. For persistent capacity issues, see [Degraded Mode](degraded-mode.md)

## Verification

After recovery:

1. Confirm job is running:
   ```bash
   sky status
   ```

2. Verify checkpoint was loaded:
   ```bash
   # Check training logs for "Resuming from checkpoint" message
   ```

3. Monitor for subsequent interruptions

## Prevention

### For Researchers

- Always implement SIGTERM handlers
- Use frequent checkpointing (every 15-30 min)
- Test checkpoint/restore before long runs

### For Platform

TODO: Document platform-side improvements

- Platform checkpoint sidecar implementation
- Improved exit code handling
- Better async sync guarantees

## Escalation

Escalate to Acceleration team if:

- Multiple jobs affected simultaneously
- Node Termination Handler not functioning
- Systematic checkpoint loss
- Capacity issues lasting > 1 hour

## Related

- [Checkpointing Guide](../../guides/checkpointing.md)
- [Degraded Mode Runbook](degraded-mode.md)
- [Implementation Plan: Spot Handling](../design/implementation-plan.md#8-reliability--spot-handling)

