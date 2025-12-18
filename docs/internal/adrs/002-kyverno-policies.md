# ADR-002: Kyverno for Policy Automation

## Status

**Implemented** (partially)

## Implementation Status

| Policy | Status | Location |
|--------|--------|----------|
| EFA Environment Injection | Implemented | `platform/base/kyverno/policies/inject-efa-env.yaml` |
| HPC Toleration Injection | Implemented | `platform/base/kyverno/policies/inject-hpc-tolerations.yaml` |
| Image Signing Enforcement | Deferred | Not yet implemented |

## Context

EFA networking requires specific environment variables to function correctly:

- `FI_PROVIDER=efa`
- `FI_EFA_USE_DEVICE_RDMA=1`
- `NCCL_DEBUG=INFO`
- `NCCL_PROTO=simple`

Without these variables, NCCL silently falls back to TCP networking, running **10x slower** with no error messages. This creates a "silent degradation" problem where researchers waste compute hours without realizing the performance loss.

We need a mechanism to automatically inject these variables when EFA resources are requested.

Options evaluated:

1. **Kyverno** — Kubernetes-native policy engine
2. **OPA/Gatekeeper** — Open Policy Agent with Kubernetes integration
3. **Custom Admission Controller** — Purpose-built webhook
4. **Documentation** — Rely on researchers to set variables manually

## Decision

**Use Kyverno for automatic policy-based configuration injection.**

Policies implemented:
- `inject-efa-env.yaml`: Inject EFA environment variables when `vpc.amazonaws.com/efa` resource requested
- `inject-hpc-tolerations.yaml`: Add tolerations/nodeSelectors for HPC taints

Policies deferred:
- `kyverno-image-signing.yaml`: Enforce image signing requirements (requires registry/key configuration)

## Consequences

### Positive

- **Eliminates silent degradation**: EFA always configured correctly when requested
- **Zero researcher burden**: Researchers request resources, platform handles details
- **Kubernetes-native**: No external dependencies, declarative YAML policies
- **Auditable**: Policy decisions logged, violations visible
- **Extensible**: Easy to add new policies (FSx PVC attachment, etc.)

### Negative

- **Webhook latency**: ~10-50ms added to pod admission
- **Learning curve**: Team needs to understand Kyverno policy language
- **Debugging complexity**: Mutations can be hard to trace
- **Dependency**: Platform relies on Kyverno being healthy

### Neutral

- Policies need maintenance as requirements evolve
- Need monitoring for policy engine health

## Alternatives Considered

### Alternative A: OPA/Gatekeeper

**Description**: Use Open Policy Agent with Gatekeeper for Kubernetes.

**Why rejected**:
- Rego language has steeper learning curve than Kyverno YAML
- Gatekeeper historically focused on validation, not mutation
- Kyverno's Kubernetes-native approach felt more natural

**When to use**: If team has existing OPA expertise or complex cross-resource policies.

### Alternative B: Custom Admission Controller

**Description**: Build a purpose-built webhook for EFA injection.

**Why rejected**:
- Custom code requires maintenance
- Reinventing solved problems
- Less flexible for future policy needs
- No community support

**When to use**: Very specific requirements not met by existing engines.

### Alternative C: Documentation Only

**Description**: Document required environment variables, rely on researchers.

**Why rejected**:
- **Fundamentally incompatible with RX goals**
- Silent degradation will occur
- Researchers shouldn't need infrastructure knowledge
- Violates "automation over documentation" principle

**When to use**: Never for production platforms.

## Implementation Notes

### EFA Environment Injection Policy

The policy watches for pods requesting `vpc.amazonaws.com/efa` and mutates to add environment variables:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: inject-efa-env
spec:
  background: true
  rules:
    - name: inject-efa-environment
      match:
        any:
          - resources:
              kinds:
                - Pod
      preconditions:
        all:
          - key: "{{ request.object.spec.containers[?resources.limits.\"vpc.amazonaws.com/efa\"] | length(@) }}"
            operator: GreaterThan
            value: 0
      mutate:
        foreach:
          - list: "request.object.spec.containers[]"
            patchesJson6902: |-
              - op: add
                path: /spec/containers/{{elementIndex}}/env/-
                value:
                  name: FI_PROVIDER
                  value: "efa"
              # ... additional variables
```

See [`platform/base/kyverno/policies/inject-efa-env.yaml`](../component-reference/kyverno.md) for full implementation.

### HPC Toleration Injection Policy

The policy adds tolerations and nodeSelector when pods are annotated with `skypilot.co/hpc=true`:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: inject-hpc-tolerations
spec:
  background: true
  rules:
    - name: inject-hpc-tolerations
      match:
        any:
          - resources:
              kinds:
                - Pod
      preconditions:
        all:
          - key: "{{ request.object.metadata.annotations.\"skypilot.co/hpc\" || '' }}"
            operator: Equals
            value: "true"
      mutate:
        patchStrategicMerge:
          spec:
            tolerations:
              - key: nvidia.com/gpu
                operator: Exists
                effect: NoSchedule
              - key: skyhook.io/workload
                operator: Equal
                value: hpc
                effect: NoSchedule
            nodeSelector:
              skyhook.io/tier: hpc
```

See [`platform/base/kyverno/policies/inject-hpc-tolerations.yaml`](../component-reference/kyverno.md) for full implementation.

## References

- [Kyverno Documentation](https://kyverno.io/)
- [Kyverno Component Reference](../component-reference/kyverno.md)
- [Slide Content: Kyverno Automation](../design/slide-content.md#slide-6-automated-configuration---kyverno-policy-engine)
- [Implementation Plan: Automation](../design/implementation-plan.md#6-automation-kyverno)
