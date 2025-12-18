# ADR-001: FSx for Lustre over Mountpoint for S3

## Status

Accepted

## Context

ML training workloads require high-throughput, low-latency access to large datasets. Storage architecture is the "gravamen" of the platform—poor storage choices create bottlenecks that starve expensive GPUs of data.

We evaluated three primary storage options:

1. **Mountpoint for S3** — Direct S3 access via FUSE filesystem
2. **FSx for Lustre** — Managed parallel filesystem with S3 integration
3. **EBS Volumes** — Traditional block storage

The key requirements are:

- Full POSIX compliance (file locking, partial writes, atomic renames)
- High throughput (saturate GPU data pipelines)
- Compatibility with existing ML training code
- Support for checkpointing without code changes

## Decision

**Use FSx for Lustre (Scratch deployment type) as the primary shared storage, with automated NVMe RAID0 for local caching.**

Configuration:
- FSx mounted at `/mnt/data` for training data
- NVMe RAID0 at `/mnt/local-scratch` for checkpoints and cache
- S3 linked to FSx for lazy loading and async export

## Consequences

### Positive

- **Full POSIX compliance**: Researchers don't need to modify code for storage limitations
- **1200 Gbps throughput**: Via EFA using SRD protocol, no I/O bottlenecks
- **Transparent caching**: FSx lazy-loads from S3, researchers see a fast filesystem
- **Checkpoint acceleration**: MOUNT_CACHED writes to NVMe, async upload to S3
- **4-15x faster** than direct S3 access depending on workload

### Negative

- **Higher cost**: FSx has per-GB cost vs S3's pay-per-request model
- **Operational complexity**: FSx lifecycle management (TTL, quotas, cleanup)
- **AZ constraints**: FSx is single-AZ, complicates multi-AZ failover
- **Provisioning time**: FSx creation takes ~10 minutes vs instant S3

### Neutral

- Need to manage FSx scratch lifecycle (TTL, data repo sync cadence)
- NVMe RAID0 requires Karpenter automation in user-data

## Alternatives Considered

### Alternative A: Mountpoint for S3

**Description**: Use S3 directly via Mountpoint FUSE driver.

**Why rejected**:
- Limited POSIX support — fails on random writes, file locking, directory renames
- Slow metadata operations — listing millions of files is orders of magnitude slower
- Creates "leaky abstraction" forcing researchers to refactor code
- Sequential read performance is good, but overall RX is poor

**When to use**: Read-only inference workloads where POSIX isn't required.

### Alternative B: EBS Volumes Only

**Description**: Use EBS gp3/io2 volumes for all storage.

**Why rejected**:
- Network-attached storage adds latency
- Single-node attachment limits sharing
- Cost scales poorly with large datasets
- Not designed for parallel I/O patterns

**When to use**: Single-node workloads with modest data requirements.

### Alternative C: Self-Managed Lustre

**Description**: Deploy and manage Lustre cluster directly.

**Why rejected**:
- Significant operational burden
- Requires Lustre expertise
- FSx provides managed equivalent with better AWS integration
- Not cost-effective at our scale

## References

- [AWS FSx for Lustre Documentation](https://docs.aws.amazon.com/fsx/latest/LustreGuide/)
- [Slide Content: Storage Trilemma](../design/slide-content.md#slide-3-storage-architecture---the-storage-trilemma)
- [Implementation Plan: Storage Layer](../design/implementation-plan.md#2-storage-layer)

