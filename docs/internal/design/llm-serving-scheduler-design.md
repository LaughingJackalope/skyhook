# LLM Serving Scheduler Design

## Overview
This document outlines the configuration and architecture of the LLM Serving Scheduler.

## Configuration
- **Scheduler Type**: Configurable between FIFO and Round Robin.
- **Resource Allocation**: Dynamic based on load and resource availability.
- **Health Checks**: Regular checks to ensure all nodes are operational.

## Architecture
- **Components**:
  - **Scheduler**: Core component that manages task distribution.
  - **Worker Nodes**: Responsible for executing tasks.
  - **Load Balancer**: Distributes incoming requests to worker nodes.

- **Flow**:
  1. Incoming request is received by the Load Balancer.
  2. The Load Balancer forwards the request to the Scheduler.
  3. The Scheduler allocates resources and assigns the task to an available Worker Node.

## Future Considerations
- Explore integration with cloud-based resource management for scalability.
- Consider implementing a priority queue for task management.

### deeper notes 
I see what you're getting at. Let me review the key architectural patterns in llm-d that make it so flexible, then we can design how to bring that same level of pluggability to Skyhook.Perfect. Now I see the full picture. Let me synthesize this into a strategic design document that aligns with both Skyhook's layered configurability philosophy and llm-d's plugin architecture. Your intuition is spot-on—intelligent, dynamic scheduling is critical.Perfect — you're asking exactly the right question, and your instinct is spot-on. Let me articulate what I'm seeing:

## **Why Configurability Matters for LLM-D in Skyhook**

### The Architecture Alignment

**Skyhook's strength**: Operators control the platform through configuration, not code changes. You see this everywhere:
- Foundation parameters (FSx capacity, subnet design) → modifiable via JSON
- Karpenter NodePools → configured via YAML, easy to add/modify
- Platform components → Helm values with Kustomize overlays

**llm-d's strength**: Scheduling is *entirely pluggable and parameterized*. This is critical because:

```
Filters (what pods are eligible) 
    ↓
Scorers (how good is each pod for THIS request?)
    ↓ 
Selection (pick best pod)
```

Every stage is configurable without touching core code. And crucially — **the same plugin type can be instantiated multiple times with different parameters**, enabling multiple scheduling profiles for different scenarios.

---

## **Why This Matters for Your Research Platform**

### Dynamic, Non-Obvious Scheduling Requirements

Here are things that will come up in a real research cluster, and you'll want to tune *without* rebuilding the scheduler:

| Scenario | Need | llm-d Solution |
|----------|------|---|
| **High cache reuse period** (10am: many similar jobs) | Maximize KV cache hits | Increase `precise-prefix-cache-scorer` weight |
| **Spot instance wave (prices drop)** | Maximize throughput, allow latency variance | Switch to aggressive `load-aware-scorer`, reduce latency weights |
| **Mixed workload (long-context + short)** | Route smartly by context | Use `context-length-aware` scorer with pod labels |
| **Model benchmark runs** | Isolate from batch inference | Use `by-label-selector` filter + dedicated pod pool |
| **Researcher wants deterministic routing** | Session affinity only | Swap `session-affinity-scorer` weight to 100 |
| **GPU shortage, fairness needed** | LRU distribution of cold requests | Enable `no-hit-lru-scorer` |

**Without plugin configurability**: Each of these would require code changes, recompilation, redeployment.

**With it**: Config change + restart (or even hot-reload if implemented).

---

## **How to Design the Config Surface in Skyhook**

Given your existing patterns, here's what I'd propose:

### **Tier 1: Operator-Level Configuration (Platform Layer)**

Store in `platform/08-apps/llm-d-dispatch/config/` as ConfigMaps and Secrets:

```
platform/08-apps/llm-d-dispatch/
├── helmrelease.yaml
├── config/
│   ├── base-scheduler-config.yaml       # Default profiles
│   ├── scorers-config.yaml              # Scorer instances & weights
│   └── filters-config.yaml              # Filter instances & rules
└── kustomization.yaml
```

**Example: base-scheduler-config.yaml (ConfigMap)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: llm-d-scheduler-config
  namespace: inference
data:
  scheduler.yaml: |
    apiVersion: inference.networking.x-k8s.io/v1alpha1
    kind: EndpointPickerConfig
    plugins:
    # Tokenizer (needed for context-aware routing)
    - name: tokenizer
      type: tokenizer
      parameters:
        modelName: "meta-llama/Llama-3.1-70B-Instruct"
        udsTokenizerConfig:
          socketFile: /tmp/tokenizer/tokenizer-uds.socket
    
    # Cache scorer (KV cache locality)
    - name: cache-scorer
      type: precise-prefix-cache-scorer
      parameters:
        tokenProcessorConfig:
          blockSize: 64
          hashSeed: "42"
        indexerConfig:
          kvBlockIndexConfig:
            enableMetrics: true
          tokenizersPoolConfig:
            modelName: "meta-llama/Llama-3.1-70B-Instruct"
    
    # Load scorer (queue depth)
    - name: load-scorer
      type: load-aware-scorer
      parameters:
        threshold: 32
    
    # Session affinity (reuse same pod)
    - name: affinity-scorer
      type: session-affinity-scorer
    
    # Context-aware routing
    - name: context-scorer
      type: context-length-aware
      parameters:
        label: llm-d.ai/context-length-range
        enableFiltering: false  # Score only, don't filter
    
    # Filters
    - name: decode-filter
      type: decode-filter
    
    - name: model-filter
      type: by-label-selector
      parameters:
        matchLabels:
          llm-d.ai/model: "llama-70b"
    
    # Selection
    - name: max-picker
      type: max-score-picker
    
    # Profile handler
    - name: profile-handler
      type: single-profile-handler
    
    schedulingProfiles:
    - name: default
      plugins:
      - pluginRef: tokenizer
      - pluginRef: model-filter
      - pluginRef: decode-filter
      - pluginRef: cache-scorer
        weight: 50      # ← Tunable weight
      - pluginRef: load-scorer
        weight: 20      # ← Tunable weight
      - pluginRef: affinity-scorer
        weight: 10      # ← Tunable weight
      - pluginRef: context-scorer
        weight: 5       # ← Tunable weight
      - pluginRef: max-picker
```

### **Tier 2: Environment-Level Tuning (via params/ files)**

Similar to how you have `foundation/params/accel-usw2.json`, you'd have scheduler profiles:

```
platform/08-apps/llm-d-dispatch/
├── params/
│   ├── cache-heavy.yaml     # Profile for high-reuse periods
│   ├── load-balanced.yaml   # Fair-share profile
│   └── low-latency.yaml     # Minimize tail latency (fewer cached, more parallel)
```

**Example: params/cache-heavy.yaml**

```yaml
# For use when you know many similar jobs will run
# Heavily favor KV cache locality
cacheScorerWeight: 100
loadScorerWeight: 5
affinityScorerWeight: 1
maxPrefixBlocksToMatch: 512  # More aggressive caching
```

### **Tier 3: Researcher-Steerable (Optional)**

Allow researchers (via SkyPilot annotations or a scheduling preference) to hint at a profile:

```yaml
# researcher-task.yaml
name: my-inference-job
annotations:
  llm-d.io/scheduling-profile: "cache-heavy"  # or "low-latency"
  llm-d.io/preferred-context-range: "0-4096"  # Optional steering
...
```

---

## **Implementation Roadmap (Addressing Your Arch Questions)**

I'd suggest tackling these in order, with configurability baked in from the start:

### **Phase 1: Core Scaffold + Base Configuration (Weeks 1–2)**

- ✅ Create `platform/08-apps/llm-d-dispatch/` with HelmRelease
- ✅ Create initial `scheduler.yaml` ConfigMap with default plugins/profiles
- ✅ Create `platform/08-apps/vllm-serving/` with pod labels (`llm-d.ai/role`, `llm-d.ai/context-length-range`)
- ✅ Document: "How to Tune Scheduler Weights"

### **Phase 2: Multi-Profile Support (Weeks 3–4)**

- ✅ Add 2–3 pre-baked profiles (`cache-heavy`, `load-balanced`, `low-latency`)
- ✅ Implement ConfigMap reload mechanism (rolling restart or native hot-reload if available)
- ✅ Expose weights and key parameters as separate ConfigMaps for easy tuning
- ✅ Document: "When to use which profile"

### **Phase 3: Observability for Tuning (Week 5+)**

- ✅ Wire metrics from llm-d into Prometheus (request routing histograms, scorer distributions)
- ✅ Add Grafana dashboard: "Scheduler decisions by profile"
- ✅ Create runbook: "How to identify if your scheduling config needs tuning"

### **Phase 4: Researcher Experimentation (Future)**

- ✅ Expose profile hints via SkyPilot annotations
- ✅ A/B test different profiles for different user cohorts

---

## **Config Management Pattern (Aligns with Skyhook Philosophy)**

You'd manage this just like your foundation/cluster tiers:

```makefile
# platform/08-apps/llm-d-dispatch/Makefile

.PHONY: config-deploy
config-deploy:
	kubectl apply -f config/base-scheduler-config.yaml
	# Optional: reload scheduler pods if needed
	kubectl rollout restart deployment llm-d-scheduler -n inference

.PHONY: config-switch-profile
config-switch-profile:  # Takes PROFILE=cache-heavy, etc.
	kustomize edit set configmapkey llm-d-scheduler-config scheduler.yaml \
	  --source file://params/$(PROFILE).yaml
	make config-deploy
```

---

## **Key Design Principles**

1. **No code changes for tuning**: Operator changes config, not Go code
2. **Layered defaults**: Start with sensible defaults, override by profile or parameter
3. **Observable tuning**: Metrics show you if your weights are working
4. **Researcher transparency**: They can see (via docs/runbooks) what profile was used and why
5. **Backward compat**: New profiles don't break existing ones

---