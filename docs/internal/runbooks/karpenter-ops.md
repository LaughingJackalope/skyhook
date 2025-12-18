# Karpenter Operations Runbook

Operational procedures for managing Karpenter in Skyhook clusters.

## Quick Reference

```bash
# Check NodePool and EC2NodeClass status
kubectl get nodepools,ec2nodeclasses

# Check Karpenter controller logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter -f

# Force Karpenter to re-evaluate pending pods
kubectl rollout restart deployment karpenter -n karpenter

# Check what nodes Karpenter has provisioned
kubectl get nodes -l karpenter.sh/nodepool
```

## Current Configuration

### NodePools

| NodePool | EC2NodeClass | Capacity | Taints | Weight |
|----------|--------------|----------|--------|--------|
| `general-purpose` | default | spot+od | none | 10 |
| `compute-optimized` | default | spot+od | none | 20 |
| `memory-optimized` | default | spot+od | none | 20 |
| `gpu-standard` | gpu | on-demand | `nvidia.com/gpu` | 30 |
| `gpu-spot` | gpu | spot | `nvidia.com/gpu`, spot | 40 |
| `hpc-distributed` | hpc | on-demand | `nvidia.com/gpu`, hpc | 50 |

### EC2NodeClasses

| Class | Subnets | AMI | Instance Profile |
|-------|---------|-----|------------------|
| `default` | System (3 AZs) | AL2023 | `{cluster}-karpenter-node` |
| `gpu` | HPC (2 AZs) | AL2 | `{cluster}-karpenter-node` |
| `hpc` | HPC (2 AZs) | AL2 | `{cluster}-karpenter-node` |

## Common Issues

### EC2NodeClass Not Ready

**Symptoms**: `kubectl get ec2nodeclasses` shows `READY=False`

**Diagnosis**:

```bash
kubectl describe ec2nodeclass <name>
```

Look for conditions:
- `SecurityGroupsReady=False`: Security group discovery failed
- `SubnetsReady=False`: Subnet discovery failed
- `AMIsReady=False`: AMI lookup failed
- `InstanceProfileReady=False`: Instance profile not found

**Fix - Security Groups Not Found**:

```bash
# Check if security group has discovery tag
aws ec2 describe-security-groups \
  --filters "Name=tag:karpenter.sh/discovery,Values=skyhook-accel-usw2-v42" \
  --query 'SecurityGroups[*].GroupId'

# Add tag if missing
aws ec2 create-tags \
  --resources sg-XXXXX \
  --tags Key=karpenter.sh/discovery,Value=skyhook-accel-usw2-v42
```

**Fix - Subnets Not Found**:

```bash
# Check subnet tags
aws ec2 describe-subnets \
  --filters "Name=tag:skyhook.io/subnet-role,Values=system" \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}'

# Verify EC2NodeClass uses correct tag
kubectl get ec2nodeclass default -o yaml | grep -A5 subnetSelectorTerms
```

**Fix - Instance Profile Not Found**:

```bash
# Check if instance profile exists
aws iam get-instance-profile \
  --instance-profile-name skyhook-accel-usw2-v42-karpenter-node

# If missing, update IAM stack
cd cluster/
make iam-update ENV=accel-usw2 CLUSTER=v42
```

### NodePool Not Ready

**Symptoms**: `kubectl get nodepools` shows `READY=False`

**Diagnosis**:

```bash
kubectl describe nodepool <name>
```

Usually caused by EC2NodeClass not ready. Fix the EC2NodeClass first.

### Nodes Not Provisioning

**Symptoms**: Pods stuck in Pending, no new nodes appearing

**Diagnosis**:

```bash
# Check pending pods
kubectl get pods -A --field-selector=status.phase=Pending

# Check Karpenter logs
kubectl logs -n karpenter -l app.kubernetes.io/name=karpenter --tail=100 | grep -E "(ERROR|WARN|provisioning)"

# Check NodeClaims
kubectl get nodeclaims
```

**Common causes**:

1. **No matching NodePool**: Pod requirements don't match any NodePool
2. **Limits exceeded**: NodePool CPU/memory limits reached
3. **IAM issues**: Karpenter can't launch instances
4. **Capacity issues**: No EC2 capacity in requested instance types

**Fix - Check NodePool limits**:

```bash
kubectl get nodepools -o custom-columns='NAME:.metadata.name,CPU:.spec.limits.cpu,MEMORY:.spec.limits.memory,USED_CPU:.status.resources.cpu,USED_MEMORY:.status.resources.memory'
```

**Fix - IAM issues**:

```bash
# Check Karpenter ServiceAccount
kubectl get sa karpenter -n karpenter -o yaml | grep -A3 annotations

# Verify IAM role exists
aws iam get-role --role-name skyhook-accel-usw2-v42-karpenter

# Update IAM if needed
cd cluster/
make iam-update ENV=accel-usw2 CLUSTER=v42

# Restart Karpenter
kubectl rollout restart deployment karpenter -n karpenter
```

### Karpenter Version Incompatibility

**Symptoms**: Karpenter pods crash with "karpenter version is not compatible with K8s version"

**Fix**: Update Karpenter version in HelmRelease:

```bash
# Check current K8s version
kubectl version --short

# Edit HelmRelease
kubectl edit helmrelease karpenter -n flux-system
# Change spec.chart.spec.version to compatible version

# Or update the file
vim platform/base/karpenter/helmrelease.yaml
kubectl apply -k platform/base/
```

**Compatibility Matrix**:

| Karpenter | Kubernetes |
|-----------|------------|
| v1.2.x | 1.29-1.32 |
| v1.1.x | 1.28-1.31 |
| v1.0.x | 1.27-1.30 |

## Upgrading Karpenter

### Pre-Upgrade Checklist

1. Check current version: `kubectl get deployment karpenter -n karpenter -o jsonpath='{.spec.template.spec.containers[0].image}'`
2. Review [release notes](https://github.com/aws/karpenter-provider-aws/releases)
3. Check for CRD changes (NodePool, EC2NodeClass API changes)
4. Backup existing NodePools and EC2NodeClasses

### Upgrade Procedure

```bash
# 1. Update HelmRelease version
vim platform/base/karpenter/helmrelease.yaml
# Change version: "1.2.0" to new version

# 2. Apply changes
kubectl apply -k platform/base/

# 3. Monitor rollout
kubectl rollout status deployment karpenter -n karpenter

# 4. Verify NodePools still work
kubectl get nodepools,ec2nodeclasses
```

### Rollback

```bash
# Revert HelmRelease version
vim platform/base/karpenter/helmrelease.yaml
kubectl apply -k platform/base/

# Or use Helm directly
helm rollback karpenter -n karpenter
```

## Adding a New NodePool

### 1. Define the NodePool

Add to `platform/base/karpenter/nodepools.yaml`:

```yaml
apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: my-new-pool
spec:
  template:
    metadata:
      labels:
        skyhook.io/pool: my-new-pool
    spec:
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default  # or gpu, hpc
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: karpenter.k8s.aws/instance-family
          operator: In
          values: ["m5", "m6i"]
      expireAfter: 720h
  limits:
    cpu: 500
  disruption:
    consolidationPolicy: WhenEmptyOrUnderutilized
    consolidateAfter: 1m
  weight: 25
```

### 2. Apply Changes

```bash
kubectl apply -k platform/base/
kubectl get nodepools
```

## Adding a New EC2NodeClass

For special instance configurations (custom AMI, special networking):

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: my-custom-class
spec:
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        skyhook.io/subnet-role: system
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: skyhook-accel-usw2-v42
  instanceProfile: skyhook-accel-usw2-v42-karpenter-node
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
  tags:
    skyhook.io/nodeclass: my-custom-class
```

## Draining Nodes

### Drain All Karpenter Nodes

```bash
# Delete all NodeClaims (triggers graceful drain)
kubectl delete nodeclaims --all

# Or delete specific NodePool's nodes
kubectl delete nodeclaims -l karpenter.sh/nodepool=gpu-spot
```

### Cordon Specific Node

```bash
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

## Monitoring

### Key Metrics

| Metric | Description |
|--------|-------------|
| `karpenter_nodes_total` | Total nodes managed by Karpenter |
| `karpenter_pods_state` | Pods by state (pending, running) |
| `karpenter_nodeclaims_created_total` | NodeClaims created |
| `karpenter_nodeclaims_terminated_total` | NodeClaims terminated |
| `karpenter_provisioner_scheduling_duration_seconds` | Scheduling latency |

### Grafana Dashboard

Karpenter metrics are exposed to Prometheus. Check the "Karpenter" dashboard in Grafana.

## Related Documentation

- [Architecture](../../architecture.md)
- [Instance Types](../../reference/instance-types.md)
- [Platform Base Reference](../component-reference/platform-base.md)
- [Karpenter Documentation](https://karpenter.sh/docs/)

## Troubleshooting - Advanced Scenarios (Karpenter v1 + EKS Pod Identity)

### 1. Error: `label domain "karpenter.k8s.aws" is restricted`

**Symptom**: Karpenter logs show `Reconciler error` with message `Invalid value: "string": label domain "karpenter.k8s.aws" is restricted` when creating NodeClaims.

**Cause**:
- **Outdated CRDs**: The cluster has old Karpenter CRDs (v1beta1 or older) that conflict with v1 validation logic.
- **Legacy Webhooks**: An old `ValidatingWebhookConfiguration` (e.g., `validation.webhook.provisioners.karpenter.sh`) from a previous installation is intercepting and rejecting requests.
- **Invalid Requirements**: Using restricted keys like `karpenter.k8s.aws/instance-family` in `NodePool` requirements (use `node.kubernetes.io/instance-type` instead).

**Fix**:
1. **Upgrade CRDs manually**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/aws/karpenter-provider-aws/v1.2.0/pkg/apis/crds/karpenter.sh_nodepools.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/karpenter-provider-aws/v1.2.0/pkg/apis/crds/karpenter.sh_nodeclaims.yaml
   kubectl apply -f https://raw.githubusercontent.com/aws/karpenter-provider-aws/v1.2.0/pkg/apis/crds/karpenter.k8s.aws_ec2nodeclasses.yaml
   ```
2. **Delete Legacy Webhooks**:
   ```bash
   kubectl delete validatingwebhookconfiguration validation.webhook.provisioners.karpenter.sh validation.webhook.config.karpenter.sh
   kubectl delete mutatingwebhookconfiguration defaulting.webhook.provisioners.karpenter.sh
   ```
3. **Restart Karpenter**: `kubectl rollout restart deployment -n karpenter karpenter`

### 2. Error: `UnauthorizedOperation` (EC2 API Denied)

**Symptom**: Karpenter logs show `AccessDenied` or `UnauthorizedOperation` when calling EC2 APIs (e.g., `DescribeLaunchTemplates`, `RunInstances`).

**Cause**:
- **Identity Mismatch**: Karpenter Controller is failing to assume its IRSA role and falling back to the Node IAM Role (which lacks permissions).
- **EKS Pod Identity Failure**: If `eks-pod-identity-agent` is installed, it requires the IAM Role Trust Policy to allow `pods.eks.amazonaws.com` principal. Legacy OIDC trust policies are not sufficient if the OIDC webhook is missing or disabled.

**Fix**:
1. **Update IAM Role Trust Policy**: Ensure `KarpenterControllerRole` trusts the EKS Pod Identity service.
   ```json
   {
       "Effect": "Allow",
       "Principal": { "Service": "pods.eks.amazonaws.com" },
       "Action": [ "sts:AssumeRole", "sts:TagSession" ]
   }
   ```
2. **Create Pod Identity Association**:
   ```bash
   aws eks create-pod-identity-association --cluster-name <cluster> --namespace karpenter --service-account karpenter --role-arn <karpenter-role-arn>
   ```
3. **Verify Env Vars**: Check if `AWS_CONTAINER_CREDENTIALS_FULL_URI` is injected into the Karpenter pod.

### 3. Error: Node Not Registered (`NodeNotFound`)

**Symptom**: `NodeClaim` status shows `Launched=True` but `Registered=Unknown`. Nodes appear in EC2 console but not in `kubectl get nodes`.

**Cause**: The IAM Role used by the Node (Instance Profile) is not mapped to Kubernetes groups (`system:nodes`) in the `aws-auth` ConfigMap or EKS Access Entries.

**Fix**:
1. **Identify Node Role**: Check `EC2NodeClass` -> `instanceProfile` -> Role ARN.
2. **Patch `aws-auth`**:
   ```bash
   kubectl edit configmap aws-auth -n kube-system
   ```
   Add:
   ```yaml
   - rolearn: arn:aws:iam::<account>:role/<cluster>-karpenter-node
     groups:
       - system:bootstrappers
       - system:nodes
     username: system:node:{{EC2PrivateDNSName}}
   ```

### 4. Error: `EC2NodeClass ... is terminating, treating as not found`

**Symptom**: Karpenter logs show errors resolving NodeClasses because they are stuck in `Terminating` state.

**Cause**: You attempted to delete `EC2NodeClass` but the controller lacked permissions (see Issue #2) to clean up resources (Launch Templates), so the finalizer blocks deletion.

**Fix**:
1. **Fix Controller Permissions** (Issue #2).
2. **Force Remove Finalizers** (if you want to reset):
   ```bash
   kubectl patch ec2nodeclass default -p '{"metadata":{"finalizers":null}}' --type=merge
   ```
3. **Re-apply Manifests**.




