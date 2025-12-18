# Internal Documentation

**For the Acceleration Team**

This section contains internal documentation for building, operating, and maintaining the Skyhook platform.

## Quick Links

### Design & Architecture

- [Design Documents](design/index.md) — Architecture decisions and rationale
- [Architecture Notes](design/architecture-notes.md) — Component overview
- [Implementation Plan](design/implementation-plan.md) — Execution roadmap

### Operations

- [Runbooks](runbooks/index.md) — Operational procedures
- [Spot Recovery](runbooks/spot-recovery.md) — Handling spot interruptions
- [Degraded Mode](runbooks/degraded-mode.md) — Operating without full capacity
- [Tenant Onboarding](runbooks/tenant-onboarding.md) — Adding new users/teams

### Technical Reference

- [Component Reference](component-reference/index.md) — Manifest documentation
- [ADRs](adrs/index.md) — Architecture Decision Records

## Repository Structure

```
SM-13/
├── clusters/           # Flux cluster configurations
├── control/            # Control plane components (quotas, scheduling)
├── docs/               # This documentation
├── helm-charts/        # Custom Helm charts
├── infra/              # Infrastructure as Code
│   ├── bootstrap/      # Flux bootstrap
│   ├── cloudformation/ # CFN templates
│   └── terraform/      # TF modules
├── platform/           # Platform components (CSI, CNI, observability)
├── policies/           # Guard rules
├── scripts/            # Tooling and CI helpers
├── skypilot-infra/     # Karpenter and Kyverno configs
└── workloads/          # Workload templates and overlays
```

## Key Contacts

TODO: Add team contacts and escalation paths.

## Related Resources

- [SkyPilot Documentation](https://skypilot.readthedocs.io/)
- [Karpenter Documentation](https://karpenter.sh/)
- [Kyverno Documentation](https://kyverno.io/)

