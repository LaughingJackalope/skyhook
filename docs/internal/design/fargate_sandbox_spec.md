# Specification: Fargate Sandbox for Untrusted Agents

## 1. Overview
This document specifies the architecture and configuration for the "Prison Pod" sandbox—a secure, isolated environment within the Skyhook cluster designed to execute untrusted code (e.g., malicious agents in the Alignment League).

By leveraging **AWS Fargate** for compute, we shift the isolation boundary from the container runtime (shared kernel) to the hypervisor (MicroVM), providing defense-in-depth against container escapes.

## 2. Threat Model & Mitigations

| Threat | Mitigation Strategy |
|--------|---------------------|
| **Container Escape** | **Fargate MicroVMs**: Agents run on dedicated Firecracker microVMs. A kernel panic or escape only compromises the ephemeral VM, not the cluster node. |
| **Lateral Movement** | **Network Policies**: Strict "Default Deny" egress policy. Agents cannot communicate with each other or scan the VPC. |
| **Data Exfiltration** | **No Internet Access**: The `untrusted` namespace has no route to the Internet Gateway or NAT Gateway (enforced by Network Policy and subnet routing). |
| **Persistence** | **Ephemeral Storage**: Fargate storage is ephemeral. No FSx mounts or PersistentVolumes are provisioned. |
| **IAM Privilege Escalation** | **No IAM Role**: The Pod Identity/IRSA configuration for this namespace is empty. |

## 3. Architecture Design

### 3.1. Compute Layer: EKS Fargate
Instead of scheduling on the existing Karpenter-managed EC2 nodes (which share kernels and have high-performance networking), untrusted workloads will run on Fargate.

**Fargate Profile Configuration:**
- **Namespace:** `untrusted`
- **Labels:** `role: agent`
- **Subnets:** Private subnets (no direct internet access).

### 3.2. Network Layer
The sandbox relies on Kubernetes NetworkPolicies (enforced by the VPC CNI) to create a "digital air gap."

- **Default Policy:** Deny ALL Ingress and Egress for the `untrusted` namespace.
- **Exception:** Allow Ingress on TCP port `8080` (or configured agent port) *only* from the Game Runner's namespace.
- **DNS:** Block access to CoreDNS to prevent internal service discovery/reconnaissance.

## 4. Configuration Specification

### 4.1. Cluster Config (`cluster/eksctl-template.yaml`)
Add the Fargate profile definition to the cluster creation template.

```yaml
fargateProfiles:
  - name: sandbox-profile
    selectors:
      - namespace: untrusted
        labels:
          role: agent
    # Use private subnets to ensure no public IP assignment
    subnets:
      - ${PRIVATE_SUBNET_1}
      - ${PRIVATE_SUBNET_2}
```

### 4.2. Kubernetes Manifests
These resources define the security boundary.

#### Namespace
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: untrusted
  labels:
    security-zone: sandbox
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

#### Network Policies

**1. Default Deny All (The Wall)**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-traffic
  namespace: untrusted
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**2. Game Runner Access (The Hatch)**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-runner-ingress
  namespace: untrusted
spec:
  podSelector:
    matchLabels:
      role: agent
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: game-system
      podSelector:
        matchLabels:
          app: game-runner
    ports:
    - protocol: TCP
      port: 8080
```

### 4.3. Pod Specifications (The Prisoner)
Agents must be launched with a strict security context to minimize the attack surface inside the VM.

```yaml
apiVersion: v1
kind: Pod
metadata:
  namespace: untrusted
  labels:
    role: agent
spec:
  # No Service Account means no API access token is mounted
  automountServiceAccountToken: false
  
  # Fargate isolation
  runtimeClassName: null # Fargate doesn't use RuntimeClasses, but explicit is good
  
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault

  containers:
  - name: agent
    image: <untrusted-image>
    ports:
    - containerPort: 8080
    
    # Resource Quotas (Prevent noisy neighbor / denial of wallet)
    resources:
      limits:
        cpu: "1"
        memory: "2Gi"
      requests:
        cpu: "0.5"
        memory: "512Mi"

    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop: ["ALL"]
    
    # Scratch space (if needed, strictly limited)
    volumeMounts:
    - name: scratch
      mountPath: /tmp
  
  volumes:
  - name: scratch
    emptyDir:
      sizeLimit: "500Mi"
```

## 5. Implementation Roadmap

1.  **Modify Template**: Update `cluster/eksctl-template.yaml` to include the `fargateProfiles` block.
2.  **Deploy Policies**: Create a new Kustomize directory `platform/05-policy/sandbox` containing the Namespace and NetworkPolicy definitions.
3.  **Update CI/CD**: Ensure the new policy directory is applied during cluster bootstrap.
4.  **Verification**:
    *   Launch a test pod in `untrusted`.
    *   Verify it runs on Fargate (check node name/type).
    *   Attempt `curl google.com` (should timeout).
    *   Attempt `curl kubernetes.default` (should timeout).
    *   Attempt to read `/var/run/secrets/kubernetes.io/serviceaccount/token` (should fail/not exist).
