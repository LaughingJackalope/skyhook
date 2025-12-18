# Platform Configuration Conformance Report

**Date:** 2025-12-06
**Scope:** `platform/base` configurations vs. Cluster `HelmRelease` resources (namespace: `flux-system`)

## Summary

| Metric | Count |
| :--- | :--- |
| **Expected Resources (Files)** | 15 |
| **Actual Resources (Cluster)** | 14 |
| **Matches** | 14 |
| **Missing in Cluster** | 1 |

## Detailed Comparison

| Resource Name | Expected Version | Cluster Status | Notes |
| :--- | :--- | :--- | :--- |
| `aws-ebs-csi-driver` | 2.32.0 | ✅ Present | |
| `aws-efs-csi-driver` | 2.5.5 | ✅ Present | |
| `aws-fsx-csi-driver` | 1.6.1 | ✅ Present | |
| `aws-load-balancer-controller` | 1.9.2 | ✅ Present | |
| `aws-node-termination-handler` | 0.21.0 | ✅ Present | |
| `aws-vpc-cni` | 1.18.2 | ✅ Present | |
| `dcgm-exporter` | 3.4.2 | ✅ Present | |
| `external-dns` | 1.15.0 | ✅ Present | |
| `fluent-bit` | 0.46.6 | ✅ Present | |
| `gatekeeper` | 3.15.1 | ✅ Present | |
| `k8sgpt-operator` | 0.2.3 | ❌ **MISSING** | Included in `platform/base/kustomization.yaml` but not found in cluster. |
| `karpenter` | 1.2.0 | ✅ Present | |
| `keda` | 2.14.0 | ✅ Present | |
| `kube-prometheus-stack` | 61.2.0 | ✅ Present | |
| `secrets-store-csi-driver` | 1.4.5 | ✅ Present | |

## Findings

1.  **Missing Component**: The `k8sgpt-operator` HelmRelease is defined in `platform/base/k8sgpt/helmrelease.yaml` and referenced in `platform/base/kustomization.yaml`, but the resource does not exist in the `flux-system` namespace in the cluster. This suggests it has not been applied or failed to sync.

2.  **Version Consistency**: All other 14 components are present in the cluster. (Note: Only existence was verified, deeper version mismatch checks would require parsing live resource spec).
