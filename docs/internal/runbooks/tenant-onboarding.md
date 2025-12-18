# Tenant Onboarding Runbook

## Overview

This runbook covers the process for onboarding a new research team or tenant to the Skyhook platform.

## Prerequisites

- Admin access to the cluster
- AWS IAM permissions for IRSA setup
- Information from new tenant:
  - Team/project name
  - Primary contact
  - Expected workload (GPU types, scale)
  - Data access requirements (S3 buckets, FSx)

## Onboarding Checklist

- [ ] Create namespace
- [ ] Configure IRSA role
- [ ] Set resource quotas
- [ ] Configure network policies
- [ ] Grant S3/FSx access
- [ ] Provide access credentials
- [ ] Schedule onboarding session
- [ ] Document in tenant registry

## Procedure

### Step 1: Create Namespace

```bash
# Create namespace
kubectl create namespace <tenant-name>

# Add standard labels
kubectl label namespace <tenant-name> \
  skyhook.io/tenant=<tenant-name> \
  skyhook.io/environment=production
```

Or apply via manifest:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: <tenant-name>
  labels:
    skyhook.io/tenant: <tenant-name>
    skyhook.io/environment: production
```

### Step 2: Configure IRSA Role

TODO: Add specific IRSA configuration

```bash
# Create IAM role for tenant
# Role should have least-privilege access to:
# - Their S3 bucket(s)
# - FSx (if dedicated)
# - ECR (read-only for images)

# Associate with service account
kubectl create serviceaccount <tenant-name>-sa -n <tenant-name>
kubectl annotate serviceaccount <tenant-name>-sa -n <tenant-name> \
  eks.amazonaws.com/role-arn=arn:aws:iam::<account>:role/<tenant-role>
```

### Step 3: Set Resource Quotas

Apply quota based on tenant tier:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: <tenant-name>-quota
  namespace: <tenant-name>
spec:
  hard:
    # GPU quota
    requests.nvidia.com/gpu: "16"
    limits.nvidia.com/gpu: "16"
    # EFA quota
    requests.vpc.amazonaws.com/efa: "4"
    # CPU/Memory defaults
    requests.cpu: "100"
    requests.memory: "400Gi"
    # Pod limits
    pods: "50"
```

TODO: Define standard quota tiers

| Tier | GPUs | EFA Interfaces | Notes |
|------|------|----------------|-------|
| Standard | 8 | 2 | Default |
| Research | 32 | 8 | For larger projects |
| Priority | 64 | 16 | Pre-approved |

### Step 4: Configure Network Policies

Apply default deny + required allowlists:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: <tenant-name>
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-required
  namespace: <tenant-name>
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  # DNS
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: UDP
      port: 53
  # FSx endpoints
  - to:
    - ipBlock:
        cidr: <fsx-cidr>
    ports:
    - protocol: TCP
      port: 988
  # Metrics/logging
  - to:
    - namespaceSelector:
        matchLabels:
          name: monitoring
```

### Step 5: Grant Data Access

#### S3 Access

Update IRSA policy to include tenant's S3 bucket:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::<tenant-bucket>",
    "arn:aws:s3:::<tenant-bucket>/*"
  ]
}
```

#### FSx Access

TODO: Document FSx access configuration

- Shared FSx: Configure subdirectory permissions
- Dedicated FSx: Provision and mount for tenant

### Step 6: Provide Access

1. **Kubeconfig**: Generate tenant-scoped kubeconfig
   ```bash
   # Create role binding for tenant namespace access
   kubectl create rolebinding <tenant-name>-edit \
     --clusterrole=edit \
     --user=<tenant-user> \
     -n <tenant-name>
   ```

2. **SkyPilot Configuration**: Provide SkyPilot setup instructions

3. **ECR Access**: Ensure tenant can pull from shared ECR repos

### Step 7: Onboarding Session

Schedule 30-minute session covering:

1. Platform overview (5 min)
2. Submitting first job (10 min)
3. Checkpointing best practices (5 min)
4. Finding logs (5 min)
5. Q&A (5 min)

Provide:
- Link to [Quick Start Guide](../../guides/quick-start.md)
- Link to [Checkpointing Guide](../../guides/checkpointing.md)
- Contact information for support

### Step 8: Document Tenant

Add to tenant registry (TODO: define location):

| Field | Value |
|-------|-------|
| Tenant Name | |
| Namespace | |
| Primary Contact | |
| Onboarding Date | |
| Quota Tier | |
| IRSA Role ARN | |
| S3 Bucket(s) | |
| Notes | |

## Verification

```bash
# Verify namespace exists
kubectl get namespace <tenant-name>

# Verify quota applied
kubectl describe quota -n <tenant-name>

# Verify service account
kubectl get sa -n <tenant-name>

# Verify network policies
kubectl get networkpolicies -n <tenant-name>

# Test job submission (as tenant)
# ...
```

## Offboarding

When removing a tenant:

1. Notify tenant of offboarding date
2. Backup any critical data
3. Delete namespace (cascades to all resources)
4. Remove IRSA role
5. Update tenant registry

```bash
kubectl delete namespace <tenant-name>
# Delete IAM role via Terraform/CloudFormation
```

## Escalation

Escalate if:
- Tenant requires non-standard access
- Custom quota beyond Priority tier
- Cross-namespace networking needed
- Dedicated FSx required

## Related

- [Limits & Quotas](../../platform/limits.md)
- [Security & Tenancy in Implementation Plan](../design/implementation-plan.md#1-security--tenancy-foundations)

