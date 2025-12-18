# Design Documentation

This section contains the architectural design documentation for Skyhook, including component decisions, implementation plans, and supporting diagrams.

## Documents

| Document | Description |
|----------|-------------|
| [Architecture Notes](architecture-notes.md) | High-level component overview and key decisions |
| [Implementation Plan](implementation-plan.md) | Step-by-step execution roadmap |
| [Slide Content](slide-content.md) | Comprehensive presentation with embedded diagrams |

## Diagrams

Mermaid diagrams for each architectural component are available in the [diagrams/](diagrams/) folder:

1. `01_system_overview.mmd` — System architecture overview
2. `02_storage_trilemma.mmd` — Storage decision tree
3. `03_storage_dataflow.mmd` — FSx + NVMe data flow
4. `04_efa_networking.mmd` — EFA networking stack
5. `05_karpenter_provisioning.mmd` — Node provisioning flow
6. `06_kyverno_automation.mmd` — Policy injection
7. `07_observability_pipeline.mmd` — Fluent Bit logging
8. `08_soci_image_loading.mmd` — SOCI lazy loading
9. `09_spot_interruption.mmd` — Spot handling sequence
10. `10_placement_groups.mmd` — Cluster placement topology
11. `11_decision_matrix.mmd` — Architectural decision ranking
12. `12_complete_flow.mmd` — End-to-end flow

## Key Architectural Decisions

### The "High-Performance Way"

Skyhook's architecture inverts the typical Kubernetes prioritization of operational simplicity over raw performance. Key decisions:

| Domain | Easy Way | High-Performance Way |
|--------|----------|---------------------|
| Storage | Mountpoint for S3 | FSx for Lustre + NVMe RAID0 |
| Networking | Standard VPC CNI | EFA + Kyverno auto-config |
| Images | Standard pull | SOCI lazy loading |
| Observability | Container Insights | Fluent Bit + task tagging |
| Reliability | Blind restart | SIGTERM + MOUNT_CACHED |

### Hardening Gaps

The following gaps have been identified for future work:

- **Resiliency**: Multi-AZ fallback, degraded mode
- **Security/Tenancy**: Per-tenant isolation, IRSA scoping
- **Provisioning**: Health checks, fail-fast bootstrap
- **Spot Handling**: Platform-side checkpoint sidecar
- **Observability**: DCGM metrics, cost attribution
- **SOCI**: Fallback behavior, signed images

## Supporting Materials

- `SkyPilotEKSRXOptimizationStrategies.txt` — Source research notes
- `High-Performance Compute-as-a-Service Architecture.pptx` — Presentation file

