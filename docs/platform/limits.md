# Limits & Quotas

> TODO: Populate with actual quota values for your environment.

## Resource Quotas

Quotas are enforced per namespace/tenant to ensure fair resource sharing.

### GPU Quotas

| Tenant Type | GPU Limit | Notes |
|-------------|-----------|-------|
| Standard | TBD | Default allocation |
| Priority | TBD | For time-sensitive projects |
| Burst | TBD | Short-term overflow |

### Storage Quotas

| Storage Type | Limit | Notes |
|--------------|-------|-------|
| FSx Usage | TBD | Shared file system quota |
| S3 Checkpoints | TBD | Per-user checkpoint bucket |
| NVMe Local | Instance-bound | Ephemeral, no quota |

### Concurrent Jobs

| Resource | Limit |
|----------|-------|
| Max concurrent jobs per user | TBD |
| Max pending jobs per user | TBD |
| Max job duration | TBD |

## Instance Availability

### Spot vs On-Demand

- **Spot instances**: Default, cost-effective, may be interrupted
- **On-demand**: Available for critical workloads (request via TBD)

### Capacity Constraints

- Cluster Placement Groups have finite capacity
- EFA-enabled instances may have regional limits
- Request capacity increases via TBD process

## Rate Limits

| Operation | Limit |
|-----------|-------|
| Job submissions per minute | TBD |
| API requests | TBD |

## Requesting Quota Increases

TODO: Document the process for requesting increased quotas.

1. Contact the Acceleration team
2. Provide justification and timeline
3. Quota adjustments take effect within TBD

## Fair Use Policy

TODO: Document any fair use expectations.

- Idle resources may be reclaimed
- Long-running jobs should checkpoint regularly
- Large allocations require advance notice

