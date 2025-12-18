# Skyhook Architecture Presentation

*Comprehensive slide deck with embedded Mermaid diagrams*

## SkyPilot on EKS: Bridging Cloud-Native and HPC for Optimal Researcher Experience

---

## Slide 1: Title Slide

**High-Performance Compute-as-a-Service Architecture**

**SkyPilot on EKS: Technology Stack for Maximum Researcher Experience**

Architectural Decisions and Requirements for HPC Research Platforms

---

## Slide 2: The Challenge - Bridging the Abstraction Gap

**Standard Kubernetes Patterns Are Insufficient for Deep Learning Workloads**

The fundamental challenge in building a Compute-as-a-Service platform lies in bridging the "gap of abstraction" between general-purpose Kubernetes constructs and the rigorous demands of high-performance computing. Standard Kubernetes prioritizes resilience and availability over raw throughput and latency—a prioritization that must be inverted for HPC workloads.

**Key Mismatches:**

- **TCP networking** is insufficient for LLM training synchronization requirements (NCCL collective operations)
- **Standard EBS volumes** introduce I/O wait times that starve expensive GPUs of data
- **Default container image pulls** create 5-10 minute startup delays that destroy interactivity
- **Generic logging** makes debugging difficult when researchers need to track jobs across pod restarts
- **Blind failure handling** wastes compute hours when spot instances are reclaimed

**Researcher Experience (RX) Definition:** Minimization of infrastructure friction—latency in job startup, complexity in data access, and opacity in failure recovery—while maximizing computational throughput and cost-efficiency.

```mermaid
graph TB
    subgraph "Researcher Interface"
        R[Researcher]
        SP[SkyPilot<br/>Abstraction Layer]
    end
    
    subgraph "AWS Cloud Infrastructure"
        subgraph "Amazon EKS Cluster"
            K8S[Kubernetes API<br/>Control Plane]
            KARP[Karpenter<br/>Auto-provisioner]
            
            subgraph "Worker Nodes"
                N1[GPU Node 1<br/>p5.48xlarge]
                N2[GPU Node 2<br/>p4d.24xlarge]
                N3[GPU Node N<br/>...]
            end
            
            subgraph "Supporting Services"
                VPC[VPC CNI<br/>+ EFA Plugin]
                FB[Fluent Bit<br/>Logging]
                KYV[Kyverno<br/>Policy Engine]
            end
        end
        
        subgraph "Storage Layer"
            S3[Amazon S3<br/>Object Storage]
            FSX[FSx for Lustre<br/>Parallel File System]
            NVM[NVMe Instance<br/>Stores RAID0]
        end
        
        subgraph "Networking"
            EFA[EFA Interfaces<br/>OS-bypass]
            CPG[Cluster Placement<br/>Groups]
        end
        
        subgraph "Observability"
            CW[CloudWatch Logs<br/>Task-based Streams]
            S3L[S3 Archive<br/>Black Box Logs]
        end
    end
    
    R -->|Submit Jobs| SP
    SP -->|Task Definition| K8S
    K8S -->|Provision Request| KARP
    KARP -->|Launch Instances| N1
    KARP -->|Launch Instances| N2
    KARP -->|Launch Instances| N3
    
    K8S --> VPC
    K8S --> KYV
    
    N1 --> NVM
    N2 --> NVM
    N3 --> NVM
    
    FSX <-->|Lazy Load| S3
    N1 <-->|Mount| FSX
    N2 <-->|Mount| FSX
    N3 <-->|Mount| FSX
    
    N1 -.->|Attached| EFA
    N2 -.->|Attached| EFA
    N3 -.->|Attached| EFA
    
    EFA -.->|Physical Proximity| CPG
    
    N1 -->|Logs| FB
    N2 -->|Logs| FB
    N3 -->|Logs| FB
    
    FB -->|Task-tagged| CW
    FB -->|Backup| S3L
    
    KYV -.->|Auto-inject<br/>EFA env vars| N1
    KYV -.->|Auto-inject<br/>EFA env vars| N2
    KYV -.->|Auto-inject<br/>EFA env vars| N3
    
    style SP fill:#4A90E2
    style KARP fill:#E27D60
    style FSX fill:#85C88A
    style EFA fill:#F4A261
    style KYV fill:#9B59B6
```

---

## Slide 3: Storage Architecture - The Storage Trilemma

**FSx for Lustre + NVMe RAID0 Provides Full POSIX Compliance with 1200 Gbps Throughput**

The storage subsystem is the gravamen of any ML platform. The architectural decision involves complex trade-offs between POSIX compliance, throughput performance, cost, and operational complexity.

**Storage Options Comparison:**

| Option | Pros | Cons |
|--------|------|------|
| Mountpoint for S3 | Cost-effective, easy setup | Limited POSIX, slow metadata |
| FSx for Lustre | Full POSIX, 1200 Gbps, S3 integration | Higher cost |
| NVMe Instance Stores | Millions of IOPS, microsecond latency | Ephemeral |

**Recommended Architecture:** FSx for Lustre Scratch + automated NVMe RAID0 for local caching and checkpoint acceleration.

```mermaid
graph TD
    START[Storage Decision<br/>for ML Workloads]
    
    START --> Q1{POSIX<br/>Compliance<br/>Required?}
    
    Q1 -->|No<br/>Read-only<br/>Inference| MP[Mountpoint for S3]
    Q1 -->|Yes<br/>Training with<br/>Checkpoints| Q2{Performance<br/>Requirements?}
    
    Q2 -->|Basic<br/>Single Node| EBS[EBS Volumes<br/>gp3/io2]
    Q2 -->|High Performance<br/>Multi-node| FSX_DECISION[FSx for Lustre]
    
    FSX_DECISION --> FSX_TYPE{Deployment<br/>Type?}
    
    FSX_TYPE -->|Temporary<br/>Processing| SCRATCH[Scratch FS<br/>S3-linked Cache]
    FSX_TYPE -->|Long-term<br/>Persistent| PERSISTENT[Persistent FS<br/>Full Copy]
    
    SCRATCH --> NVME_Q{Local NVMe<br/>Available?}
    PERSISTENT --> NVME_Q
    EBS --> NVME_Q
    
    NVME_Q -->|Yes| RAID[NVMe RAID0<br/>Local Cache]
    NVME_Q -->|No| SKIP[Skip Local<br/>Optimization]
    
    style START fill:#4A90E2
    style SCRATCH fill:#85C88A,stroke:#2D5F3E,stroke-width:3px
    style RAID fill:#85C88A,stroke:#2D5F3E,stroke-width:3px
```

---

## Slide 4: Storage Data Flow - From S3 to GPU

**FSx Lazy-Loading with NVMe Caching Eliminates I/O Bottlenecks**

```mermaid
graph LR
    subgraph "Object Storage"
        S3[(Amazon S3<br/>Training Data<br/>Checkpoints)]
    end
    
    subgraph "FSx for Lustre Scratch"
        FSX_META[Metadata Servers<br/>MDT]
        FSX_DATA[Object Storage<br/>Targets OST]
    end
    
    subgraph "GPU Instance p5.48xlarge"
        POD[Training Pod]
        MOUNT[/mnt/data]
        NVME[/mnt/local-scratch<br/>NVMe RAID0]
    end
    
    S3 <-->|Lazy Load| FSX_DATA
    FSX_DATA <-->|1200 Gbps<br/>via EFA| MOUNT
    POD --> MOUNT
    POD --> NVME
    MOUNT -.->|MOUNT_CACHED<br/>Async Upload| S3
```

---

## Slide 5: High-Performance Networking - EFA and OS-Bypass

**Elastic Fabric Adapter Reduces Multi-Node Training Latency by 10x Through Kernel Bypass**

| Path | Latency | Throughput |
|------|---------|------------|
| Traditional TCP | High (kernel overhead) | Limited |
| EFA OS-Bypass | Low (direct hardware) | 400 Gbps per interface |

```mermaid
graph TB
    APP[Training Code] --> NCCL[NCCL Collectives]
    NCCL --> LIBFABRIC[libfabric]
    
    LIBFABRIC -->|FI_PROVIDER=efa| EFA[EFA Hardware]
    LIBFABRIC -.->|Fallback 10x slower| TCP[TCP Stack]
    
    EFA --> NET[AWS Network<br/>400 Gbps]
    
    style EFA fill:#85C88A
    style TCP fill:#F8D7DA
```

---

## Slide 6: Automated Configuration - Kyverno Policy Engine

**Kyverno Policies Prevent Silent Performance Degradation by Auto-Injecting EFA Configuration**

When pods request `vpc.amazonaws.com/efa`, Kyverno automatically injects:

- `FI_PROVIDER=efa`
- `FI_EFA_USE_DEVICE_RDMA=1`
- `NCCL_DEBUG=INFO`
- `NCCL_PROTO=simple`

```mermaid
graph LR
    POD[Pod with EFA request] --> API[API Server]
    API --> KYV[Kyverno]
    KYV -->|Inject env vars| FINAL[Pod with EFA config]
    FINAL --> SCHED[Scheduler]
    
    style KYV fill:#9B59B6
    style FINAL fill:#85C88A
```

---

## Slide 7: Cluster Placement Groups

**Placement Groups Reduce Network Latency from 100-500μs to 10-20μs Through Physical Proximity**

| Configuration | Latency | GPU Utilization |
|---------------|---------|-----------------|
| Within Placement Group | 10-20 μs | 90% |
| Scattered (no CPG) | 100-500 μs | 60-70% |

---

## Slide 8: Observability - User-Centric Logging

**Task-Based Log Streams Reduce Mean Time to Debug**

- SkyPilot labels pods with `skypilot.task_id`
- Fluent Bit rewrites tags to route by task
- All retries/restarts in single CloudWatch stream: `/skypilot/user-jobs/task-<id>`

---

## Slide 9: Image Vending - SOCI Lazy Loading

**SOCI Snapshotter Reduces Container Startup Time by 50%+**

| Approach | Startup Time |
|----------|--------------|
| Traditional pull | 5-10 minutes |
| SOCI lazy loading | Seconds |

---

## Slide 10: Failure Handling - Graceful Spot Interruption Recovery

**SIGTERM Signal Handling with MOUNT_CACHED Checkpoints Prevents Wasted Compute Hours**

```python
import signal
import sys

def graceful_exit(signum, frame):
    print("Caught SIGTERM. Saving emergency checkpoint...")
    save_checkpoint()  # Write to local NVMe
    sys.exit(0)  # Exit code 0 = retry-able event

signal.signal(signal.SIGTERM, graceful_exit)
```

---

## Slide 11: Karpenter Provisioning - Automated Node Configuration

**Provisioning Sequence:**

1. Researcher submits SkyPilot task
2. Karpenter provisions GPU node
3. User data configures NVMe RAID0
4. FSx mounted via CSI
5. Kyverno injects EFA config
6. SOCI lazy-loads image
7. Training starts

---

## Slide 12: Decision Matrix - Ranked Architectural Choices

| Rank | Domain | Easy Way | High-Performance Way | Impact |
|------|--------|----------|---------------------|--------|
| 1 | Storage | S3 Mountpoint | FSx + NVMe | Critical |
| 2 | Networking | VPC CNI | EFA + Kyverno | High |
| 3 | Images | Standard pull | SOCI | High |
| 4 | Observability | Container Insights | Fluent Bit + tagging | Medium |
| 5 | Ephemeral Storage | EBS only | NVMe RAID0 | Medium |
| 6 | Reliability | Blind restart | SIGTERM + MOUNT_CACHED | Medium |

---

## Slide 13: Hardening & Fallback Plan (Gaps to Close)

**Resiliency**

- Multi-AZ fallback, degraded mode without EFA/placement groups
- FSx scratch lifecycle management

**Security & Tenancy**

- Per-tenant namespaces + IRSA
- GPU/EFA quotas, NetworkPolicies
- Image signing/verification

**Provisioning Robustness**

- Health checks for RAID/FSx/EFA setup
- Fail-fast on errors

**Spot Handling**

- Platform-side checkpoint sidecar
- Ensure S3 persistence before termination

**Observability**

- DCGM GPU metrics
- Cost attribution per task

**SOCI & Supply Chain**

- Fallback when index missing
- Image signing enforcement

