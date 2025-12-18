# Runbooks

Operational procedures for the Skyhook platform.

## Available Runbooks

| Runbook | When to Use |
|---------|-------------|
| [Karpenter Operations](karpenter-ops.md) | Node provisioning issues, NodePool/EC2NodeClass problems |
| [Spot Recovery](spot-recovery.md) | Spot instance interrupted, job not recovering |
| [Degraded Mode](degraded-mode.md) | Capacity constrained, need to operate without full features |
| [Tenant Onboarding](tenant-onboarding.md) | Adding new research team to the platform |
| [K8sGPT Operations](k8sgpt-ops.md) | AI-powered diagnostics, MCP server access, Bedrock issues (incubating) |

## Runbook Format

Each runbook follows this structure:

1. **Symptoms** — How to recognize the situation
2. **Impact** — What's affected
3. **Prerequisites** — Access/tools needed
4. **Procedure** — Step-by-step actions
5. **Verification** — How to confirm resolution
6. **Escalation** — When to escalate and to whom

## Quick Reference

### Common Commands

```bash
# Check cluster health
kubectl get nodes -o wide

# View pending pods
kubectl get pods --all-namespaces --field-selector=status.phase=Pending

# Check Karpenter status
kubectl get nodepools
kubectl get ec2nodeclasses

# View Kyverno policies
kubectl get clusterpolicies
```

### Key Dashboards

- **Cluster Overview**: Grafana → Dashboards → Kubernetes / Compute Resources / Cluster
- **Node Health**: Grafana → Dashboards → Kubernetes / Compute Resources / Node
- **NTH Events**: CloudWatch Logs → `/aws/eks/<cluster>/nth`

### Alerting

Alerts are routed through Alertmanager. Key alert channels:

- **Slack**: `#skyhook-alerts` for platform events
- **PagerDuty**: Critical alerts (node failures, capacity exhaustion)

### Node Termination Handler

The platform uses AWS Node Termination Handler (NTH) in SQS queue mode to detect:

- Spot Instance Interruption Warnings (2-minute notice)
- EC2 Rebalance Recommendations (proactive migration signal)
- Scheduled Maintenance Events (AWS Health)

NTH automatically cordons and drains nodes before termination, giving pods time to checkpoint and gracefully exit.

```bash
# Check NTH status
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-node-termination-handler

# View NTH logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-node-termination-handler --tail=100

# Check for recent termination events
kubectl get events -A --field-selector reason=NodeTermination
```

