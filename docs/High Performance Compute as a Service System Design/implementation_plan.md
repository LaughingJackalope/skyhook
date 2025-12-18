# Implementation Plan (Execution-Ready)

Ordered steps to move from architecture to running HPCaaS on EKS/SkyPilot. Each step is scoped to produce a verifiable artifact (manifest, policy, script, or test).

## 0) Prereqs & Baseline
- Choose control plane: EKS cluster version (>=1.29) with Bottlerocket workers, containerd with SOCI snapshotter available.
- Enable IAM Roles for Service Accounts (IRSA); confirm OIDC provider.
- Create base VPC with adequate /16 and per-AZ /19 to host placement groups and EFA ENIs.

## 1) Security & Tenancy Foundations
- Namespaces per tenant; bind IRSA roles to least-privileged S3/FSx access.
- Apply Pod Security Standards (baseline/restricted) and default NetworkPolicies (deny-all + allow to FSx endpoints, metrics, logging).
- Enforce image signing/verification (e.g., cosign policy/kyverno) and registry auth.
- Define GPU/EFA resource quotas per namespace; set LimitRanges for CPU/memory defaults.

## 2) Storage Layer
- Provision FSx for Lustre:
  - Choose mode per workload: scratch (TTL e.g., 24–72h) with data-repo sync every N hours; persistent for long-running datasets.
  - Record mount targets per AZ; enable data repository export for checkpoints; document quotas and cleanup workflow.
- Author PV/PVC templates referencing FSx CSI; include mount options and performance configs.
- Define NVMe RAID0 bootstrap script (systemd unit) with device filtering to avoid root; emit health signals on success/failure.
- FSx mount health: in user-data, mount via FSX_DNS (SSM param or instance tag), fail fast on errors, persist fstab; log when skipped.

## 3) Networking (EFA + Placement)
- Pre-create cluster placement groups (e.g., `ml-cpg-a`, `ml-cpg-b`) sized for target node counts; parameterize in `karpenter-hpc.yaml`.
- Optionally bind a launch template name in EC2NodeClass if LT manages placement/AMI tweaks; ensure EFA networkInterfaces set.
- Verify VPC CNI + EFA plugin versions; enable prefix delegation if needed; note required CNI/EFA versions in docs.
- Define “degraded mode” scheduling class that omits placement groups/EFA for capacity fallback (added in `karpenter-hpc.yaml`).

## 4) Provisioning (Karpenter)
- Define EC2NodeClass with:
  - Instance families (p5/p5e/p4d as available), EFA=true, AMI=Bottlerocket, launchTemplateName set to placement-aware LT.
  - User data that: stops kubelet, RAIDs NVMe, mounts /mnt/local-scratch, restarts kubelet, and logs status.
- Define NodePools with consolidation off for HPC jobs; set TTL for empty nodes; add taints for HPC-only scheduling.
- Add readiness/health checks to fail node registration if RAID/FSx/EFA setup fails.

## 5) Image Vending (SOCI)
- Enable SOCI snapshotter in containerd; ensure Bottlerocket variant supports it.
- Pre-compute SOCI indices for standard ML images; store alongside images in ECR.
- Define fallback: if SOCI index missing, allow full pull; document expected latency impact.
- Add NVMe cache path for SOCI to use /mnt/local-scratch.

## 6) Automation (Kyverno)
- Policy to inject EFA env vars (`FI_PROVIDER=efa`, `FI_EFA_USE_DEVICE_RDMA=1`, `NCCL_PROTO=simple`, `NCCL_DEBUG=INFO`) when `vpc.amazonaws.com/efa` requested (`skypilot-infra/kyverno-efa-env.yaml`).
- Policy to add tolerations/nodeSelectors for HPC taints when annotated (`skypilot.co/hpc=true`) (`skypilot-infra/kyverno-hpc-toleration.yaml`).
- Policy to enforce allowed registries + cosign verification annotation (`skypilot-infra/kyverno-image-signing.yaml`); tune registries/key as needed.
- Policy to auto-attach FSx PVC/PV by label or annotation (placeholder to add if desired).

## 6a) Security & Tenancy Guidance
- Per-tenant namespaces with IRSA roles scoped to tenant S3/FSx; default deny NetworkPolicies plus allowlists to FSx endpoints/metrics/logging.
- GPU/EFA resource quotas and LimitRanges per namespace to cap burst; optional ResourceQuota for PVC counts/size.
- Secrets via AWS Secrets Manager/Parameter Store CSI drivers; avoid static long-lived keys.

## 7) Observability
- Deploy DCGM Exporter for GPU metrics; scrape via Prometheus, surface via Grafana.
- Fluent Bit pipeline with task-based tagging (SkyPilot labels -> CloudWatch log groups `/skypilot/user-jobs/task-*`) and S3 archival; set retention budgets (e.g., CW 7-14d, S3 30-90d).
- Capture boot/provision timings (user-data logs) and EFA/NCCL transport selection (env + NCCL debug logs).
- Cost and duration attribution per task: emit Prometheus metrics keyed by `skypilot.task_id`.
- Add dashboards for: GPU util/mem, EFA throughput/errors, FSx throughput/latency, pod start latency (SOCI impact).

## 8) Reliability & Spot Handling
- Install Node Termination Handler wired to SQS/IMDS for spot events.
- Provide platform-side pre-stop hook/sidecar to catch SIGTERM and write emergency checkpoint to NVMe, then trigger async upload to S3; standardize exit codes for SkyPilot to treat as preemptible (e.g., 0 or custom retryable code).
- Configure MOUNT_CACHED mode for checkpoint buckets; verify async export back to S3 on drain.
- Add pod annotation or sidecar to ensure flush on `preStop`; document how to include in SkyPilot templates.
- Test degraded mode (no EFA/placement) and resume-from-checkpoint flows.

## 9) Testing Matrix (Minimal)
- Single-node training: FSx + NVMe, SOCI cold start vs warm start timings.
- Multi-node with EFA: NCCL all-reduce latency/throughput; verify Kyverno env injection.
- Spot interruption: SIGTERM -> checkpoint -> reschedule -> resume.
- Fallback path: capacity pressure -> schedule without placement group/EFA.
- Security: unsigned image blocked; namespace quota enforcement; network policy isolation.

### Smoke Commands (examples)
- Manifests dry run (no cluster access required): `make dry-run-manifests`
- FSx mount check (on node): `mount | grep lustre && dd if=/dev/zero of=/mnt/fsx/test bs=1M count=1024`
- NCCL/EFA quick check: run `nccl-tests/all_reduce_perf -b 8 -e 1G -f 2 -g 8` in a 2-node job; confirm transport `efa` in logs.
- SOCI cold-start timing: schedule pod with large image and measure `ContainerCreating` duration; compare with and without SOCI index.
- Spot simulation (if allowed): `aws ec2 terminate-instances --instance-ids <id>` on a spot node or use scheduled event; watch checkpoint + reschedule.

## 10) Deliverables to Produce
- Karpenter `EC2NodeClass` and `NodePool` manifests (HPC tainted).
- Launch Templates with placement groups and EFA-enabled ENIs.
- Systemd unit or Bottlerocket bootstrap script for NVMe RAID0 + FSx mount with health reporting.
- Kyverno policies (EFA env inject, signed images, PVC attach, tolerations).
- SOCI enablement config + list of indexed base images.
- Observability manifests: DCGM exporter, Prometheus scrape configs, Fluent Bit rewrite_tag, log retention.
- Runbook: operational playbook for degraded mode, spot recovery, and FSx scratch lifecycle/TTL.

## SOCI Enablement Notes
- Enable SOCI snapshotter in containerd/Bottlerocket; set cache dir to NVMe (e.g., /mnt/local-scratch/soci-cache) via snapshotter config.
- Precompute SOCI indices for base images and push to ECR; document image:tag -> index map.
- Fallback: if index absent, allow standard pull (slower) but log warning.
- Measure cold vs warm startup with SOCI to validate cache placement.

