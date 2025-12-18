# Skyhook Foundation Layer

The foundation layer is **long-lived infrastructure** that cluster releases are built upon. It includes networking, storage, and placement groups that persist across cluster lifecycles.

## Architecture

```
Foundation Layer (months/years)
├── VPC + Subnets (HPC-optimized)
├── FSx for Lustre (persistent data lake)
├── Placement Groups (EFA networking)
├── VPC Endpoints (cost + latency optimization)
└── KMS Keys (encryption at rest)
```

## Live Environment (accel-usw2)

| Resource | Value |
|----------|-------|
| **Stack Name** | `skyhook-accel-usw2-foundation` |
| **VPC** | `vpc-092d808c1bbe46da0` |
| **VPC CIDR** | `10.0.0.0/16` |
| **Region** | `us-west-2` |
| **FSx File System** | `fs-06f749f9104b7ec01` |
| **FSx Mount Name** | `a2cfrb4v` |
| **FSx Type** | PERSISTENT_2 (125 MB/s/TiB) |
| **KMS Key** | `c3ff8c8d-0551-415b-b166-3034ac58eee5` |

## Subnet Design

| Subnet Type | CIDR Size | AZs | Purpose | Live IDs |
|-------------|-----------|-----|---------|----------|
| Public | /24 × 3 | a,b,c | NAT gateways, ALB | 3 subnets |
| System | /22 × 3 | a,b,c | EKS control plane, system pods | `subnet-02c0...`, `subnet-0414...`, `subnet-0aa8...` |
| HPC | /19 × 2 | a,b | GPU nodes with EFA | `subnet-0aaf...`, `subnet-05c0...` |
| Storage | /24 × 1 | a | FSx mount targets | `subnet-07b1...` |

## Quick Start

```bash
# 1. Create a new foundation
make foundation-up ENV=accel-usw2

# 2. Check status
make foundation-status ENV=accel-usw2

# 3. List SSM parameters
make ssm-list ENV=accel-usw2

# 4. View foundation metadata
aws ssm get-parameter \
  --name /skyhook/accel-usw2/foundation-metadata \
  --query Parameter.Value --output text | jq .
```

## Files

| File | Description |
|------|-------------|
| `templates/main.yaml` | Root CloudFormation stack |
| `templates/vpc.yaml` | VPC, subnets, routing, NAT |
| `templates/endpoints.yaml` | 13 VPC endpoints for AWS services |
| `templates/storage.yaml` | FSx for Lustre, KMS key |
| `templates/placement-groups.yaml` | 3 cluster placement groups + 1 spread |
| `params/accel-usw2.json` | Parameters for Acceleration team |
| `Makefile` | Foundation lifecycle commands |

## Creating a New Environment

1. Copy `params/accel-usw2.json` to `params/<new-env>.json`
2. Edit parameters (VPC CIDR, AZs, storage size)
3. Run `make foundation-up ENV=<new-env>`

## Parameters

| Parameter | Description | accel-usw2 Value |
|-----------|-------------|------------------|
| `Environment` | Environment ID | `accel-usw2` |
| `VpcCidr` | VPC CIDR block (must be /16) | `10.0.0.0/16` |
| `PrimaryAZ` | Primary AZ for HPC | `us-west-2a` |
| `SecondaryAZ` | Secondary AZ | `us-west-2b` |
| `TertiaryAZ` | Tertiary AZ for system | `us-west-2c` |
| `FsxStorageCapacity` | FSx capacity in GB | `1200` |
| `FsxDeploymentType` | SCRATCH_2 or PERSISTENT_2 | `PERSISTENT_2` |
| `FsxThroughput` | Throughput (MB/s/TiB) | `125` |

## SSM Parameters

The foundation publishes parameters to SSM for cluster consumption:

### Individual Parameters

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| `/skyhook/{env}/vpc-id` | VPC ID | `vpc-092d808c1bbe46da0` |
| `/skyhook/{env}/system-subnet-ids` | System subnets (CSV) | `subnet-02c0...,subnet-0414...,subnet-0aa8...` |
| `/skyhook/{env}/hpc-subnet-ids` | HPC subnets (CSV) | `subnet-0aaf...,subnet-05c0...` |
| `/skyhook/{env}/storage-subnet-id` | Storage subnet | `subnet-07b1...` |
| `/skyhook/{env}/fsx-dns-name` | FSx DNS | `fs-06f749f9104b7ec01.fsx.us-west-2.amazonaws.com` |
| `/skyhook/{env}/fsx-mount-name` | FSx mount name | `a2cfrb4v` |
| `/skyhook/{env}/fsx-file-system-id` | FSx file system ID | `fs-06f749f9104b7ec01` |
| `/skyhook/{env}/kms-key-arn` | KMS key ARN | `arn:aws:kms:us-west-2:...` |
| `/skyhook/{env}/placement-group-primary-alpha` | First placement group | `skyhook-accel-usw2-cpg-us-west-2a-alpha` |
| `/skyhook/{env}/placement-group-primary-beta` | Second placement group | `skyhook-accel-usw2-cpg-us-west-2a-beta` |
| `/skyhook/{env}/placement-groups` | All placement groups (CSV) | `...-alpha,...-beta,...` |

### Foundation Metadata (JSON)

The `/skyhook/{env}/foundation-metadata` parameter contains all values as JSON:

```json
{
  "environment": "accel-usw2",
  "region": "us-west-2",
  "vpc_id": "vpc-092d808c1bbe46da0",
  "vpc_cidr": "10.0.0.0/16",
  "primary_az": "us-west-2a",
  "secondary_az": "us-west-2b",
  "system_subnet_ids": "subnet-02c01314416286b3b,subnet-04141297cfaf62363,subnet-0aa8044a424fde00a",
  "hpc_subnet_ids": "subnet-0aafb87c85d8aca7a,subnet-05c02e2645ba8cbb6",
  "storage_subnet_id": "subnet-07b173823b167c9c9",
  "fsx_dns_name": "fs-06f749f9104b7ec01.fsx.us-west-2.amazonaws.com",
  "fsx_mount_name": "a2cfrb4v",
  "fsx_file_system_id": "fs-06f749f9104b7ec01",
  "kms_key_arn": "arn:aws:kms:us-west-2:751442549699:key/c3ff8c8d-0551-415b-b166-3034ac58eee5",
  "placement_groups": "skyhook-accel-usw2-cpg-us-west-2a-alpha,skyhook-accel-usw2-cpg-us-west-2a-beta,skyhook-accel-usw2-cpg-us-west-2b-alpha"
}
```

## Lifecycle

### Creating

```bash
make foundation-up ENV=accel-usw2
```

This will:
1. Create S3 bucket for templates (`skyhook-{env}-cfn-templates`)
2. Upload nested templates
3. Deploy CloudFormation stack
4. Publish SSM parameters

### Checking Status

```bash
make foundation-status ENV=accel-usw2
```

Output shows stack status and key outputs.

### Updating

```bash
make foundation-update ENV=accel-usw2
```

Safe updates:
- VPC endpoints
- FSx capacity (expand only)
- Placement groups (add new ones)

**Destructive updates** (require careful planning):
- VPC CIDR changes
- Subnet changes
- FSx deployment type changes

### Deleting

```bash
make foundation-down ENV=accel-usw2
```

**WARNING**: This deletes FSx and all data! Only use when decommissioning an entire environment.

## Relationship to Clusters

```
Foundation (1) ──────────── Clusters (N)
    │                           │
    ├── VPC        ←───────────┤ (referenced by SSM)
    ├── Subnets    ←───────────┤ (referenced by SSM)  
    ├── FSx        ←───────────┤ (mounted via user-data)
    └── Placement  ←───────────┤ (referenced by name)
        Groups
```

Multiple clusters can run on the same foundation:
- `skyhook-accel-usw2-v42` (production)
- `skyhook-accel-usw2-v43` (canary)
- `skyhook-accel-usw2-exp1` (experiment)

All share the same FSx data lake and VPC.

## Tagging Strategy

All foundation resources are tagged for Karpenter discovery:

| Tag | Value | Purpose |
|-----|-------|---------|
| `skyhook.io/environment` | `accel-usw2` | Environment identification |
| `skyhook.io/layer` | `foundation` | Layer identification |
| `skyhook.io/subnet-role` | `system` / `hpc` / `public` / `storage` | Subnet discovery by Karpenter |

## Troubleshooting

### Stack Creation Failed

```bash
# View detailed events
aws cloudformation describe-stack-events \
  --stack-name skyhook-accel-usw2-foundation \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
```

### FSx Mount Issues

```bash
# Verify FSx is active
aws fsx describe-file-systems \
  --file-system-ids fs-06f749f9104b7ec01 \
  --query 'FileSystems[0].Lifecycle'

# Check security groups allow Lustre traffic (port 988)
```

### SSM Parameters Missing

```bash
# Re-run stack update to refresh SSM
make foundation-update ENV=accel-usw2
```

## Disaster Recovery

### FSx Data Loss

With PERSISTENT_2 deployment:
- Automatic daily backups are enabled
- Configure S3 data repository association for additional backup

### VPC/Network Issues

Foundation VPC is isolated. If corrupted:
1. Create new foundation in different CIDR range
2. Migrate data from S3 backup to new FSx
3. Point clusters to new foundation

### Placement Group Issues

Placement groups are soft-deleted. If capacity is fragmented:
1. Create new placement groups (beta → gamma)
2. Update Karpenter EC2NodeClasses to use new groups
3. Drain old nodes
