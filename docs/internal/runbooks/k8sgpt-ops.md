# K8sGPT Operations Runbook

Operational procedures for managing K8sGPT in Skyhook clusters.

> **Status**: Incubating Component  
> **Backend**: Amazon Bedrock (Claude 3 Sonnet)

## Quick Reference

```bash
# Check K8sGPT operator status
kubectl get pods -n k8sgpt-operator-system

# Check K8sGPT custom resource status
kubectl get k8sgpt -n k8sgpt-operator-system

# View K8sGPT analysis results
kubectl get results -n k8sgpt-operator-system

# Check operator logs
kubectl logs -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt-operator -f

# Check k8sgpt deployment logs
kubectl logs -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt -f

# Manually trigger analysis
kubectl annotate k8sgpt k8sgpt -n k8sgpt-operator-system k8sgpt.ai/trigger=$(date +%s) --overwrite
```

## Architecture Overview

K8sGPT provides AI-powered Kubernetes diagnostics using Amazon Bedrock:

```
┌────────────────────────────────────────────────────────────────┐
│                     K8sGPT Architecture                        │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐     ┌──────────────────┐                 │
│  │  K8sGPT Operator│────▶│  K8sGPT Instance │                 │
│  │  (manages CRs)  │     │  (cluster scan)  │                 │
│  └─────────────────┘     └────────┬─────────┘                 │
│                                   │                            │
│                     ┌─────────────┼─────────────┐             │
│                     ▼             ▼             ▼             │
│              ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│              │ Bedrock  │  │ Results  │  │   MCP    │         │
│              │ (Claude) │  │   CRD    │  │  Server  │         │
│              └──────────┘  └──────────┘  └──────────┘         │
│                                                ▲               │
│                                                │               │
│                         Researchers via Internal ALB          │
└────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| k8sgpt-operator | k8sgpt-operator-system | Manages K8sGPT CR lifecycle |
| k8sgpt | k8sgpt-operator-system | Scans cluster, calls Bedrock |
| Results CRD | k8sgpt-operator-system | Stores analysis findings |
| MCP Service | k8sgpt-operator-system | gRPC API for external clients |

## Common Operations

### Viewing Analysis Results

K8sGPT stores analysis results as custom resources:

```bash
# List all results
kubectl get results -n k8sgpt-operator-system

# Get detailed result
kubectl describe result <name> -n k8sgpt-operator-system

# View all results as JSON
kubectl get results -n k8sgpt-operator-system -o json | jq '.items[].spec'
```

### Accessing via MCP (Researchers)

Researchers can connect to the K8sGPT MCP server via the internal ALB:

1. **Get ALB endpoint**:
   ```bash
   kubectl get ingress k8sgpt-mcp -n k8sgpt-operator-system -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
   ```

2. **Configure MCP client**: Use the ALB hostname in your MCP client configuration.

3. **Port-forward for testing** (if ALB not ready):
   ```bash
   kubectl port-forward svc/k8sgpt-mcp -n k8sgpt-operator-system 8080:8080
   ```

### Checking Bedrock Connectivity

Verify IRSA and Bedrock access:

```bash
# Check ServiceAccount annotation
kubectl get sa k8sgpt -n k8sgpt-operator-system -o yaml | grep -A2 annotations

# Check if pod has AWS credentials
kubectl exec -n k8sgpt-operator-system -it deploy/k8sgpt -- env | grep AWS

# Test Bedrock access (from pod)
kubectl exec -n k8sgpt-operator-system -it deploy/k8sgpt -- \
  aws bedrock list-foundation-models --query 'modelSummaries[?contains(modelId, `claude-3-sonnet`)]'
```

## Troubleshooting

### K8sGPT Pod Not Starting

**Symptoms**: Pod stuck in `Pending` or `CrashLoopBackOff`

**Diagnosis**:
```bash
kubectl describe pod -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt
kubectl logs -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt --previous
```

**Common causes**:

1. **IRSA not configured**: ServiceAccount missing role ARN annotation
   ```bash
   # Fix: Add annotation
   kubectl annotate sa k8sgpt -n k8sgpt-operator-system \
     eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT:role/CLUSTER-k8sgpt
   ```

2. **Image pull failure**: Check image registry access
3. **Resource limits**: Increase memory/CPU limits

### Bedrock API Errors

**Symptoms**: Logs show `AccessDeniedException` or `ValidationException`

**Diagnosis**:
```bash
kubectl logs -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt | grep -i bedrock
```

**Common causes**:

1. **Model not enabled**: Enable Claude 3 Sonnet in AWS Bedrock console
   - Go to AWS Console → Bedrock → Model access
   - Request access to `anthropic.claude-3-sonnet-20240229-v1:0`

2. **Wrong region**: Model not available in cluster region
   ```bash
   # Check K8sGPT CR region config
   kubectl get k8sgpt k8sgpt -n k8sgpt-operator-system -o yaml | grep region
   ```

3. **IAM permissions**: Update role policy
   ```bash
   # Verify IAM policy
   aws iam get-role-policy --role-name CLUSTER-k8sgpt --policy-name K8sGPTBedrockPolicy
   ```

### No Results Generated

**Symptoms**: `kubectl get results -n k8sgpt-operator-system` returns empty

**Diagnosis**:
```bash
# Check K8sGPT CR status
kubectl describe k8sgpt k8sgpt -n k8sgpt-operator-system

# Check operator logs
kubectl logs -n k8sgpt-operator-system -l app.kubernetes.io/name=k8sgpt-operator --tail=50
```

**Common causes**:

1. **No issues found**: Cluster is healthy (this is good!)
2. **Namespace filters**: K8sGPT may be filtering out problematic namespaces
   ```bash
   # Check filter config
   kubectl get k8sgpt k8sgpt -n k8sgpt-operator-system -o yaml | grep -A5 filters
   ```
3. **AI disabled**: Verify AI is enabled
   ```bash
   kubectl get k8sgpt k8sgpt -n k8sgpt-operator-system -o yaml | grep -A5 ai:
   ```

### MCP Server Not Accessible

**Symptoms**: Cannot connect to MCP endpoint

**Diagnosis**:
```bash
# Check service
kubectl get svc k8sgpt-mcp -n k8sgpt-operator-system

# Check ingress
kubectl describe ingress k8sgpt-mcp -n k8sgpt-operator-system

# Check ALB status
kubectl get ingress k8sgpt-mcp -n k8sgpt-operator-system -o yaml | grep -A10 status:
```

**Common causes**:

1. **ALB not provisioned**: Check AWS Load Balancer Controller logs
   ```bash
   kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller
   ```

2. **Security group rules**: Ensure VPC CIDR is allowed
3. **Target health**: Check target group health in AWS console

## Configuration

### Modifying Analysis Scope

Edit the K8sGPT CR to change which namespaces are analyzed:

```bash
kubectl edit k8sgpt k8sgpt -n k8sgpt-operator-system
```

```yaml
spec:
  # Analyze specific namespace only
  targetNamespace: "my-namespace"
  
  # Or exclude namespaces
  filters:
    - kube-system
    - flux-system
    - karpenter
    - observability  # Add more as needed
```

### Changing AI Model

To use a different Bedrock model:

1. **Update K8sGPT CR**:
   ```yaml
   spec:
     ai:
       model: anthropic.claude-3-haiku-20240307-v1:0  # Faster, cheaper
   ```

2. **Update IAM policy**: Add new model ARN to Bedrock permissions

### Enabling Notifications

Configure Slack notifications for findings:

```yaml
spec:
  sink:
    type: slack
    webhook:
      name: k8sgpt-slack-secret
      key: webhook-url
```

Create the secret:
```bash
kubectl create secret generic k8sgpt-slack-secret \
  -n k8sgpt-operator-system \
  --from-literal=webhook-url='https://hooks.slack.com/services/...'
```

## Upgrading K8sGPT

### Pre-Upgrade Checklist

1. Check current version: `kubectl get k8sgpt k8sgpt -n k8sgpt-operator-system -o yaml | grep version`
2. Review [release notes](https://github.com/k8sgpt-ai/k8sgpt-operator/releases)
3. Check for CRD changes

### Upgrade Procedure

```bash
# 1. Update HelmRelease version
vim platform/base/k8sgpt/helmrelease.yaml
# Change version: "0.2.3" to new version

# 2. Update K8sGPT CR version
vim platform/base/k8sgpt/k8sgpt-cr.yaml
# Change version: v0.3.41 to new version

# 3. Apply changes
kubectl apply -k platform/base/

# 4. Monitor rollout
kubectl rollout status deployment -n k8sgpt-operator-system k8sgpt-operator

# 5. Verify CR reconciled
kubectl get k8sgpt k8sgpt -n k8sgpt-operator-system
```

## Security Considerations

### IRSA Configuration

K8sGPT uses IRSA for Bedrock access. The IAM role:
- Trust policy: `k8sgpt-operator-system:k8sgpt` service account
- Permissions: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- Resource scope: Claude 3 Sonnet model ARN only

### RBAC

K8sGPT has read-only cluster access via `ClusterRole`:
- Core resources (pods, services, nodes, events)
- Workload resources (deployments, statefulsets)
- Karpenter resources (nodepools, ec2nodeclasses)

It **cannot** modify cluster resources, only analyze them.

### Network Access

MCP server is exposed via internal ALB:
- Only accessible from within VPC
- Security group restricts to VPC CIDR (10.0.0.0/16)
- No public internet access

## Metrics and Monitoring

K8sGPT exposes Prometheus metrics at `:8443/metrics`:

| Metric | Description |
|--------|-------------|
| `k8sgpt_analysis_count` | Number of analyses performed |
| `k8sgpt_results_count` | Number of issues found |
| `k8sgpt_ai_request_duration_seconds` | Bedrock API latency |

### Grafana Dashboard

Import the K8sGPT dashboard from [k8sgpt-ai/k8sgpt](https://github.com/k8sgpt-ai/k8sgpt/tree/main/dashboards).

## Related Documentation

- [K8sGPT Documentation](https://k8sgpt.ai/docs/)
- [K8sGPT Operator GitHub](https://github.com/k8sgpt-ai/k8sgpt-operator)
- [Amazon Bedrock Claude Models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
- [Karpenter Operations](karpenter-ops.md)
- [Platform Architecture](../../platform/architecture.md)

