# Quick Start

> TODO: Customize with actual cluster details and access procedures.

Submit your first GPU job on Skyhook in 5 minutes.

## Prerequisites

- [ ] Access to the Skyhook cluster (contact Acceleration team)
- [ ] SkyPilot installed (`pip install skypilot`)
- [ ] AWS credentials configured

## Step 1: Configure SkyPilot

TODO: Add actual cluster configuration steps.

```bash
# Verify SkyPilot can see the cluster
sky check
```

## Step 2: Create a Task File

Create `hello-gpu.yaml`:

```yaml
# hello-gpu.yaml
name: hello-gpu

resources:
  accelerators: A100:1
  
setup: |
  pip install torch

run: |
  python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
  python -c "import torch; print(f'Device: {torch.cuda.get_device_name(0)}')"
```

## Step 3: Launch Your Job

```bash
sky launch hello-gpu.yaml
```

SkyPilot will:

1. Find available GPU capacity
2. Provision a node (via Karpenter)
3. Pull your container image (via SOCI)
4. Run your code

## Step 4: Check Status

```bash
# View job status
sky status

# View logs
sky logs <job-id>

# SSH into the job (if still running)
sky ssh <job-id>
```

## Step 5: Clean Up

```bash
# Terminate the job
sky down <job-id>
```

## What Just Happened?

Behind the scenes, Skyhook:

- Provisioned a GPU node with NVMe RAID0 configured
- Mounted FSx for Lustre at `/mnt/data`
- Configured EFA networking (if requested)
- Set up task-based logging for easy log retrieval

## Next Steps

- [Learn about checkpointing](checkpointing.md) for long-running jobs
- [Set up multi-node training](multi-node.md) for distributed workloads
- [View available capabilities](../platform/capabilities.md)

## Common Issues

### Job stuck in "Pending"

- Check quota limits: `sky status`
- Verify capacity is available for requested instance type
- See [Debugging Guide](debugging.md)

### Image pull taking too long

- Ensure your image has a SOCI index in ECR
- Contact Acceleration team to add index for new images

### Need help?

Contact the Acceleration team.

