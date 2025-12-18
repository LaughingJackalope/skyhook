# Degraded Mode Runbook

## Overview

This runbook covers operating Skyhook in "degraded mode" when full high-performance features are unavailable due to capacity constraints, AZ issues, or component failures.

## What is Degraded Mode?

Degraded mode allows the platform to continue serving researchers with reduced performance guarantees when:

- Cluster Placement Group capacity is exhausted
- EFA-enabled instances unavailable
- Specific AZ is constrained
- FSx is experiencing issues

## Symptoms Indicating Degraded Mode May Be Needed

- Jobs pending for extended periods (> 15 minutes)
- Karpenter unable to provision requested instance types
- Placement group capacity errors
- Multi-node jobs failing to schedule together

## Impact

| Feature | Full Mode | Degraded Mode |
|---------|-----------|---------------|
| Multi-node latency | 10-20 μs | 100-500 μs |
| GPU utilization | ~90% | 60-70% |
| NCCL transport | EFA (SRD) | TCP |
| Storage | FSx + NVMe | FSx only (or fallback) |

## Prerequisites

- kubectl access with admin privileges
- Understanding of Karpenter NodePools
- Ability to communicate with affected researchers

## Procedure

### Step 1: Diagnose the Constraint

```bash
# Check pending pods
kubectl get pods --all-namespaces --field-selector=status.phase=Pending

# Check Karpenter provisioning issues
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter | grep -i "error\|failed\|insufficient"

# Check placement group capacity
aws ec2 describe-placement-groups --query 'PlacementGroups[*].[GroupName,State]'
```

### Step 2: Determine Degraded Mode Level

| Level | Condition | Action |
|-------|-----------|--------|
| Level 1 | CPG full but EFA available | Remove placement group constraint |
| Level 2 | EFA unavailable | Fall back to TCP networking |
| Level 3 | Instance type unavailable | Use alternative instance type |
| Level 4 | AZ unavailable | Route to different AZ |

### Step 3: Enable Degraded Mode

#### Level 1: Bypass Placement Group

TODO: Add specific Karpenter configuration changes

```yaml
# Modify EC2NodeClass to remove placement group
# Or use degraded NodePool without CPG constraint
```

#### Level 2: TCP Fallback

Jobs will automatically fall back to TCP if EFA is unavailable. Verify:

```bash
# Check NCCL transport in job logs
grep -i "transport\|efa\|socket" <job-logs>
```

If seeing "Socket" transport, degraded mode is active.

#### Level 3: Alternative Instance Types

```bash
# Check available capacity
aws ec2 describe-instance-type-offerings \
  --location-type availability-zone \
  --filters Name=instance-type,Values=p4d.24xlarge,p4de.24xlarge,p5.48xlarge \
  --query 'InstanceTypeOfferings[*].[InstanceType,Location]'
```

Update NodePool to allow alternative types.

#### Level 4: AZ Failover

```bash
# Check which AZs have capacity
# Update NodePool topology constraints
```

### Step 4: Communicate to Researchers

Template notification:

```
Subject: [Skyhook] Degraded Mode Active

The Skyhook platform is currently operating in degraded mode due to 
[capacity constraints / AZ issues / component maintenance].

Impact:
- Multi-node training may experience higher network latency
- Expected GPU utilization: 60-70% (vs normal 90%)
- Single-node jobs are unaffected

Affected period: [start time] - [estimated end]

Recommendations:
- Single-node jobs: No action needed
- Multi-node jobs: Consider postponing or expect longer training times

We are actively working to restore full capacity.

- Acceleration Team
```

### Step 5: Monitor Recovery

```bash
# Watch for capacity restoration
watch -n 60 'kubectl get nodepools -o wide; kubectl get pods -A --field-selector=status.phase=Pending | wc -l'
```

### Step 6: Restore Full Mode

When capacity is restored:

1. Re-enable placement group constraints
2. Verify EFA is being used for new jobs
3. Notify researchers of restoration

## Verification

Confirm degraded mode is working:

```bash
# Jobs should be scheduling (even if slower)
kubectl get pods -A | grep -v Running | grep -v Completed

# Check new pods are starting
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

## Prevention

- Monitor placement group utilization
- Set up alerts for capacity issues
- Maintain multiple AZ capability
- Document capacity limits per placement group

## Escalation

Escalate if:

- Degraded mode doesn't resolve scheduling issues
- Multiple AZs affected simultaneously
- FSx is unavailable (affects all jobs)
- Degraded mode persists > 4 hours

## Related

- [Spot Recovery Runbook](spot-recovery.md)
- [Architecture Notes: Degraded Mode](../design/architecture-notes.md)
- [Karpenter HPC Configuration](../component-reference/skypilot-infra.md)

