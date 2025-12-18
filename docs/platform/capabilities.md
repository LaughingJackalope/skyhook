# Capabilities

> TODO: Populate with actual instance types and configurations available in your cluster.

## GPU Instance Types

| Instance Type | GPUs | GPU Memory | EFA Support | NVMe Storage |
|--------------|------|------------|-------------|--------------|
| p5.48xlarge | 8x H100 | 640 GB | Yes (4x 400 Gbps) | 8x 1TB |
| p4d.24xlarge | 8x A100 | 320 GB | Yes (4x 400 Gbps) | 8x 1TB |
| p4de.24xlarge | 8x A100 80GB | 640 GB | Yes | 8x 1TB |

TODO: Add actual instance types available in your environment.

## Storage

### FSx for Lustre (Shared)

- **Mount point**: `/mnt/data`
- **Throughput**: Up to 1200 Gbps via EFA
- **Capacity**: TODO: Add quota information
- **Use for**: Training data, shared datasets, checkpoints

### NVMe Instance Storage (Local)

- **Mount point**: `/mnt/local-scratch`
- **Configuration**: RAID0 striped across all instance NVMe drives
- **Use for**: Fast local cache, temporary files, checkpoint staging

### S3 (Object Storage)

- **Access**: Via MOUNT_CACHED for checkpoints
- **Use for**: Long-term checkpoint storage, final model artifacts

## Networking

### EFA (Elastic Fabric Adapter)

- Automatically configured when requesting `vpc.amazonaws.com/efa` resource
- Environment variables auto-injected by Kyverno policies
- Required for efficient multi-node NCCL operations

### Cluster Placement Groups

- Pre-provisioned for low-latency multi-node communication
- Reduces network latency from 100-500μs to 10-20μs

## Container Images

### SOCI (Seekable OCI)

- Large ML images (15GB+) start in seconds, not minutes
- On-demand block fetching with NVMe caching
- Pre-indexed images available for common frameworks

TODO: List pre-indexed images available in ECR.

## Quotas

TODO: Document per-namespace quotas.

| Resource | Default Quota |
|----------|---------------|
| GPUs | TBD |
| Storage | TBD |
| Concurrent Jobs | TBD |

