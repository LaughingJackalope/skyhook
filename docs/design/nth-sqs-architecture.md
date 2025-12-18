# AWS Node Termination Handler: SQS Mode Architecture

## Overview

This document describes the architecture and implementation strategy for AWS Node Termination Handler (NTH) using SQS queue mode in Skyhook's multi-cluster environment.

**Status**: Proposed
**Author**: Skyhook Platform Team
**Last Updated**: 2025-12-17

## Background

AWS Node Termination Handler protects workloads from EC2 disruptions (Spot interruptions, scheduled maintenance, instance retirement) by gracefully draining nodes before termination. NTH supports two operational modes:

- **IMDS mode**: Polls EC2 instance metadata on each node (DaemonSet)
- **SQS mode**: Centralized event processor consuming from SQS queue (Deployment)

For Skyhook's multi-cluster architecture with ephemeral cluster releases, SQS mode provides better operational characteristics.

## Architecture Decision

### One Queue Per Cluster

Each EKS cluster receives its own dedicated SQS queue for termination events.

**Rationale**:

| Criterion | Benefit |
|-----------|---------|
| **Isolation** | Events routed only to relevant cluster, preventing cross-cluster noise |
| **Security** | Cluster-specific IAM permissions via IRSA, adhering to least-privilege |
| **Scaling** | Independent queue metrics and DLQ per cluster for targeted monitoring |
| **Debugging** | Clear event attribution simplifies troubleshooting |
| **Cost** | Minimal overhead (~$0.01/month per queue with standard pricing) |

**Alternatives Considered**:

- **Single shared queue**: Requires complex message filtering, creates single point of failure
- **IMDS mode**: Higher resource usage (DaemonSet on all nodes), delayed spot notifications

## Infrastructure Components

### Layer Allocation

Following Skyhook's three-layer architecture:

```
Layer 0: Foundation (months/years)
├── EventBridge rules (shared across all clusters)
├── IAM role template for NTH service accounts
└── SNS topics for event routing (optional)

Layer 1: Cluster Release (days/weeks)
├── SQS queue (cluster-specific)
├── Dead Letter Queue (cluster-specific)
├── IAM role for NTH IRSA (references OIDC provider)
└── EventBridge targets (queue subscriptions)

Layer 2: Platform Services (hours)
└── NTH Helm deployment (configured with queue URL)
```

### Foundation Layer Resources

**File**: `foundation/templates/nth-infrastructure.yaml`

Resources created once per environment:

```yaml
# EventBridge rule for EC2 Spot interruptions
SpotInterruptionRule:
  Type: AWS::Events::Rule
  Properties:
    Name: !Sub "skyhook-${Environment}-spot-interruptions"
    EventPattern:
      source: ["aws.ec2"]
      detail-type: ["EC2 Spot Instance Interruption Warning"]
    State: ENABLED

# EventBridge rule for scheduled maintenance
ScheduledChangeRule:
  Type: AWS::Events::Rule
  Properties:
    Name: !Sub "skyhook-${Environment}-scheduled-changes"
    EventPattern:
      source: ["aws.health"]
      detail-type: ["AWS Health Event"]
    State: ENABLED

# EventBridge rule for instance rebalance recommendations
RebalanceRule:
  Type: AWS::Events::Rule
  Properties:
    Name: !Sub "skyhook-${Environment}-rebalance"
    EventPattern:
      source: ["aws.ec2"]
      detail-type: ["EC2 Instance Rebalance Recommendation"]
    State: ENABLED
```

**Why foundation layer?**
- EventBridge rules are environment-scoped, not cluster-scoped
- Reduces duplication across cluster releases
- Centralized event routing configuration

### Cluster Layer Resources

**File**: `cluster/templates/nth-queue.yaml`

Resources created per cluster:

```yaml
# Primary SQS queue for NTH events
NTHQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub "nth-${ClusterName}"
    MessageRetentionPeriod: 300  # 5 minutes
    VisibilityTimeout: 30
    RedrivePolicy:
      deadLetterTargetArn: !GetAtt NTHDeadLetterQueue.Arn
      maxReceiveCount: 3
    Tags:
      - Key: skyhook.io/cluster
        Value: !Ref ClusterName
      - Key: skyhook.io/component
        Value: node-termination-handler

# Dead letter queue for failed processing
NTHDeadLetterQueue:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub "nth-${ClusterName}-dlq"
    MessageRetentionPeriod: 1209600  # 14 days
    Tags:
      - Key: skyhook.io/cluster
        Value: !Ref ClusterName
      - Key: skyhook.io/component
        Value: node-termination-handler

# Queue policy allowing EventBridge to publish
NTHQueuePolicy:
  Type: AWS::SQS::QueuePolicy
  Properties:
    Queues:
      - !Ref NTHQueue
    PolicyDocument:
      Statement:
        - Effect: Allow
          Principal:
            Service: events.amazonaws.com
          Action: sqs:SendMessage
          Resource: !GetAtt NTHQueue.Arn
```

**Why cluster layer?**
- Queue lifecycle matches cluster lifecycle
- Automatic cleanup when cluster is destroyed
- Supports blue-green cluster deployments

### EventBridge Target Registration

EventBridge rules (foundation) must target cluster-specific queues. Two approaches:

#### Approach 1: Dynamic Target Registration (Recommended)

Foundation creates rules without targets. Cluster creation adds targets via CLI:

```bash
# During cluster creation
QUEUE_ARN=$(aws cloudformation describe-stacks \
  --stack-name ${CLUSTER_NAME}-nth-queue \
  --query 'Stacks[0].Outputs[?OutputKey==`QueueArn`].OutputValue' \
  --output text)

# Register queue as target for each rule
for RULE in spot-interruptions scheduled-changes rebalance; do
  aws events put-targets \
    --rule "skyhook-${ENV}-${RULE}" \
    --targets "Id=${CLUSTER_NAME},Arn=${QUEUE_ARN}"
done
```

**Pros**: Clean separation, supports arbitrary number of clusters
**Cons**: Requires manual target registration during cluster lifecycle

#### Approach 2: SSM Parameter Discovery

Clusters publish queue ARN to SSM, foundation template references via CloudFormation:

```yaml
# In cluster stack
NTHQueueArnParameter:
  Type: AWS::SSM::Parameter
  Properties:
    Name: !Sub "/skyhook/${Environment}/clusters/${ClusterName}/nth-queue-arn"
    Value: !GetAtt NTHQueue.Arn
```

**Pros**: Automatic discovery, infrastructure-as-code
**Cons**: Foundation template needs updating when clusters change

**Decision**: Use Approach 1 (dynamic registration) to maintain foundation/cluster independence.

### IAM Configuration

NTH requires permissions to consume from SQS and describe EC2 instances.

**File**: `cluster/templates/iam-cluster.yaml` (add to existing IAM stack)

```yaml
NTHServiceAccountRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub "${ClusterName}-nth-sa"
    AssumeRolePolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Effect: Allow
          Principal:
            Federated: !Sub "arn:aws:iam::${AWS::AccountId}:oidc-provider/${OIDCProviderID}"
          Action: "sts:AssumeRoleWithWebIdentity"
          Condition:
            StringEquals:
              !Sub "${OIDCProviderID}:sub": "system:serviceaccount:kube-system:aws-node-termination-handler"
    ManagedPolicyArns:
      - !Ref NTHServiceAccountPolicy

NTHServiceAccountPolicy:
  Type: AWS::IAM::ManagedPolicy
  Properties:
    PolicyDocument:
      Version: "2012-10-17"
      Statement:
        - Sid: QueueConsumer
          Effect: Allow
          Action:
            - sqs:ReceiveMessage
            - sqs:DeleteMessage
            - sqs:GetQueueAttributes
          Resource: !Sub "arn:aws:sqs:${AWS::Region}:${AWS::AccountId}:nth-${ClusterName}"
        - Sid: EC2ReadAccess
          Effect: Allow
          Action:
            - ec2:DescribeInstances
            - autoscaling:DescribeAutoScalingInstances
            - autoscaling:DescribeTags
          Resource: "*"
```

## Deployment

### Foundation Deployment (Once per Environment)

```bash
cd foundation/
make nth-infrastructure-up ENV=accel-usw2
```

This creates:
- EventBridge rules for spot/maintenance/rebalance events
- CloudWatch Log Groups for rule monitoring

### Cluster Deployment (Per Cluster)

Integrated into `make cluster-up`:

```bash
# 1. Deploy NTH queue stack
aws cloudformation deploy \
  --template-file cluster/templates/nth-queue.yaml \
  --stack-name ${CLUSTER_NAME}-nth-queue \
  --parameter-overrides \
      ClusterName=${CLUSTER_NAME} \
      Environment=${ENV}

# 2. Register queue with EventBridge rules
QUEUE_ARN=$(aws cloudformation describe-stacks \
  --stack-name ${CLUSTER_NAME}-nth-queue \
  --query 'Stacks[0].Outputs[?OutputKey==`QueueArn`].OutputValue' \
  --output text)

for RULE in spot-interruptions scheduled-changes rebalance; do
  TARGET_ID="${CLUSTER_NAME}-$(echo $RULE | tr '-' '_')"
  aws events put-targets \
    --rule "skyhook-${ENV}-${RULE}" \
    --targets "Id=${TARGET_ID},Arn=${QUEUE_ARN}"
done

# 3. Update IAM stack with NTH role (part of make iam-update)
aws cloudformation deploy \
  --template-file cluster/templates/iam-cluster.yaml \
  --stack-name ${CLUSTER_NAME}-iam \
  --capabilities CAPABILITY_NAMED_IAM

# 4. Create ConfigMap with queue URL for Helm
QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name ${CLUSTER_NAME}-nth-queue \
  --query 'Stacks[0].Outputs[?OutputKey==`QueueURL`].OutputValue' \
  --output text)

kubectl create configmap nth-values \
  --from-literal=queueURL=${QUEUE_URL} \
  --namespace flux-system
```

### Platform Deployment (Flux)

**File**: `platform/base/nth/helmrelease.yaml`

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: aws-node-termination-handler
  namespace: flux-system
spec:
  chart:
    spec:
      chart: aws-node-termination-handler
      sourceRef:
        kind: HelmRepository
        name: eks-charts
      version: 0.21.0
  interval: 5m
  valuesFrom:
    - kind: ConfigMap
      name: nth-values
      valuesKey: queueURL
      targetPath: queueURL
  values:
    enableSqsTerminationDraining: true
    enableScheduledEventDraining: true
    enableRebalanceMonitoring: true
    enableRebalanceDraining: true

    # SQS mode runs as Deployment (not DaemonSet)
    replicas: 2

    # IRSA annotation
    serviceAccount:
      create: true
      name: aws-node-termination-handler
      annotations:
        eks.amazonaws.com/role-arn: "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${CLUSTER_NAME}-nth-sa"

    # Resource requests for centralized deployment
    resources:
      requests:
        cpu: 50m
        memory: 64Mi
      limits:
        cpu: 100m
        memory: 128Mi
```

## Operations

### Monitoring

**Metrics to track**:

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Queue depth | CloudWatch `ApproximateNumberOfMessagesVisible` | > 10 for 5 minutes |
| DLQ depth | CloudWatch `ApproximateNumberOfMessagesVisible` | > 0 |
| Processing latency | NTH Prometheus `nth_queue_receive_latency` | > 10s p95 |
| Node drain duration | NTH Prometheus `nth_node_drain_duration_seconds` | > 120s p95 |

**CloudWatch Dashboard**:

```bash
# Create per-cluster NTH dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "${CLUSTER_NAME}-nth" \
  --dashboard-body file://dashboards/nth-sqs.json
```

### Troubleshooting

**No events being processed**:

```bash
# 1. Check queue has messages
aws sqs get-queue-attributes \
  --queue-url $(kubectl get cm nth-values -n flux-system -o jsonpath='{.data.queueURL}') \
  --attribute-names ApproximateNumberOfMessages

# 2. Check EventBridge rule targets
aws events list-targets-by-rule --rule skyhook-${ENV}-spot-interruptions

# 3. Check NTH pod logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-node-termination-handler

# 4. Verify IAM permissions
kubectl describe sa aws-node-termination-handler -n kube-system
```

**Messages in DLQ**:

```bash
# Retrieve DLQ messages for analysis
aws sqs receive-message \
  --queue-url $(aws sqs get-queue-url --queue-name nth-${CLUSTER_NAME}-dlq --output text) \
  --max-number-of-messages 10

# Common causes:
# - Malformed EventBridge events
# - EC2 instance not found (node already terminated)
# - Kubernetes API timeout during drain
```

### Cleanup

When deleting a cluster:

```bash
# 1. Remove EventBridge targets
for RULE in spot-interruptions scheduled-changes rebalance; do
  TARGET_ID="${CLUSTER_NAME}-$(echo $RULE | tr '-' '_')"
  aws events remove-targets \
    --rule "skyhook-${ENV}-${RULE}" \
    --ids ${TARGET_ID}
done

# 2. Delete NTH queue stack (includes DLQ)
aws cloudformation delete-stack --stack-name ${CLUSTER_NAME}-nth-queue
```

## Cost Analysis

Per cluster (us-west-2 pricing):

| Component | Monthly Cost |
|-----------|--------------|
| SQS queue (1M requests) | $0.40 |
| DLQ storage (minimal) | $0.01 |
| EventBridge rule evaluation | $0.00 (first 2M free) |
| **Total per cluster** | **~$0.41** |

For 10 clusters: ~$4/month

## Migration Path

For existing clusters using IMDS mode:

1. Deploy NTH queue stack
2. Update NTH Helm values to enable SQS mode alongside IMDS
3. Validate SQS events processing correctly
4. Disable IMDS mode and remove DaemonSet
5. Clean up IMDS-related IAM instance profile permissions

## Future Enhancements

1. **EventBridge event filtering**: Filter events by AZ or instance type before queueing
2. **SNS fan-out**: Send events to multiple queues (multi-cluster) or notification channels
3. **Custom drain logic**: Integrate with SkyPilot to checkpoint training jobs before termination
4. **Metrics integration**: Export NTH metrics to centralized Prometheus/Grafana

## References

- [AWS Node Termination Handler Documentation](https://github.com/aws/aws-node-termination-handler)
- [EventBridge Event Patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)
- [SQS Best Practices](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-best-practices.html)
- Skyhook Architecture: `docs/architecture/layers.md`
