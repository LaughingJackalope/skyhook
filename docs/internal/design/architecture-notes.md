# Architecture Notes

*Migrated from original design documentation*

## Key Technologies and Decisions

### 1. System Overview

- **Platform**: SkyPilot on EKS (Amazon Elastic Kubernetes Service)
- **Provisioner**: Karpenter
- **Goal**: Compute-as-a-Service for researchers (maximize Researcher Experience - RX)
- **Challenge**: Bridge gap between general-purpose Kubernetes and HPC demands

### 2. Storage Architecture (The Storage Trilemma)

Three options with trade-offs:

- **Mountpoint for S3**: Easy way - cost-effective but limited POSIX compliance
- **FSx for Lustre**: High-performance way - full POSIX, 1200 Gbps throughput
- **NVMe Instance Stores**: Ephemeral, ultra-low latency, local caching

**Key Decision**: FSx for Lustre + NVMe RAID0 automation via Karpenter

### 3. Networking Architecture

- **EFA (Elastic Fabric Adapter)**: OS-bypass networking using SRD protocol
- **Cluster Placement Groups**: Physical proximity for minimal latency
- **Kyverno Policies**: Auto-inject environment variables for NCCL/EFA

**Key Decision**: EFA + automated configuration via Kyverno

### 4. Observability

- **Challenge**: Gap between SkyPilot Task IDs and Kubernetes Pod UIDs
- **Solution**: Fluent Bit with rewrite_tag for user-centric log streams
- **Spot Handling**: Node Termination Handler + "last gasp" logging to S3

### 5. Image Vending Strategy

- **Traditional**: Pre-warmed AMIs (rigid, high operational burden)
- **Modern**: SOCI (Seekable OCI) - lazy loading with NVMe caching
- **Benefit**: 50%+ reduction in startup latency

### 6. Failure Handling

- **SkyPilot Checkpointing**: MOUNT_CACHED mode for async S3 uploads
- **Spot Interruption**: SIGTERM signal handling for graceful checkpoints
- **Recovery**: Automatic rescheduling with state preservation

## Diagrams

The following diagrams document the architecture:

1. System architecture overview (SkyPilot + EKS + Karpenter)
2. Storage trilemma decision tree
3. Storage architecture with FSx + NVMe
4. EFA networking stack and configuration flow
5. Cluster placement groups topology
6. Observability pipeline (Fluent Bit rewrite)
7. SOCI image loading mechanism
8. Spot interruption handling flow
9. Karpenter node provisioning with automation
10. Decision matrix/ranking visualization
11. Complete data flow (end-to-end)
12. Failure recovery workflow

See [diagrams/](diagrams/) folder for Mermaid source files.

## Hardening Gaps to Close

### Resiliency

- Add multi-AZ fallback (or backup FSx/ONTAP) and a "degraded mode" without placement groups/EFA when capacity is scarce
- Document data repo task cadence for FSx scratch and TTL/quotas for scratch data

### Security/Tenancy

- Per-tenant namespaces + IRSA roles
- GPU/EFA quota policies
- Pod security + network policies
- Secrets management
- Image signing/verification
- Ensure FSx/S3 access is scoped per tenant

### Provisioning Robustness

- Health checks around user-data RAID/FSx/EFA bring-up (fail fast if mdadm/mount/EFA attach fails)
- Guard against device ordering nuking the root disk
- Record bootstrap timings

### Spot Handling

- Provide platform-side pre-stop hook/sidecar so emergency checkpoints happen even when user code lacks SIGTERM handlers
- Ensure checkpoints reach durable storage (S3) before node termination

### Observability

- Add DCGM GPU metrics
- NCCL/EFA transport selection
- Boot/provision latency
- Cost attribution per task
- Set CloudWatch/S3 retention budgets

### SOCI Fallbacks

- Define behavior when SOCI index is missing
- Prefetch guidance for hot libs
- Compatibility requirements (containerd/Bottlerocket)
- Integrity via signed images

