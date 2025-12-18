# ==============================================================================
# Skyhook Master Orchestrator
# ==============================================================================
# This Makefile acts as a facade, delegating commands to the specialized
# Makefiles in foundation/, cluster/, and platform/ directories.
#
# Usage:
#   make all-up ENV=accel-usw2 CLUSTER=v42
#   make foundation-up ENV=accel-usw2
#   make cluster-up ENV=accel-usw2 CLUSTER=v42
#   make platform-up
#
# ==============================================================================

ENV ?=
CLUSTER ?=

.PHONY: help all-up all-down
.PHONY: foundation-up foundation-down foundation-status
.PHONY: cluster-up cluster-down cluster-status cluster-config
.PHONY: platform-up platform-down platform-status
.PHONY: docs docs-serve docs-build

help:
	@echo "Skyhook Master CLI"
	@echo "=================="
	@echo "Usage: make <target> ENV=<env> CLUSTER=<release>"
	@echo ""
	@echo "End-to-End:"
	@echo "  all-up            - Deploy Foundation -> Cluster -> Platform"
	@echo "  all-down          - Destroy Platform -> Cluster -> Foundation"
	@echo ""
	@echo "Layer 0: Foundation (VPC, FSx)"
	@echo "  foundation-up     - Deploy foundation infrastructure"
	@echo "  foundation-down   - Destroy foundation (WARNING: Deletes Data)"
	@echo "  foundation-status - Show foundation details"
	@echo ""
	@echo "Layer 1: Cluster (EKS, IAM)"
	@echo "  cluster-up        - Create EKS cluster release"
	@echo "  cluster-down      - Destroy EKS cluster release"
	@echo "  cluster-status    - Show cluster status"
	@echo "  cluster-config    - Generate cluster config (dry-run)"
	@echo ""
	@echo "Layer 2: Platform (Karpenter, Observability)"
	@echo "  platform-up       - Deploy all platform components (via kubectl/helm)"
	@echo "  platform-down     - Uninstall all platform components"
	@echo "  platform-status   - Show platform deployment status"
	@echo ""
	@echo "Documentation:"
	@echo "  docs-serve        - Start local MkDocs server"
	@echo "  docs-build        - Build static documentation site"
	@echo ""
	@echo "Required Variables:"
	@echo "  ENV               - Environment name (e.g., accel-usw2)"
	@echo "  CLUSTER           - Cluster release tag (e.g., v42)"

# ==============================================================================
# Composite Targets
# ==============================================================================

all-up: foundation-up cluster-up platform-up
	@echo "==> Skyhook stack deployed successfully!"

# Interactive confirmation for all-down is handled by sub-makefiles
all-down: platform-down cluster-down foundation-down
	@echo "==> Skyhook stack destroyed."

# ==============================================================================
# Layer Delegation
# ==============================================================================

# --- Foundation ---
foundation-up:
	$(MAKE) -C foundation foundation-up ENV=$(ENV)

foundation-down:
	$(MAKE) -C foundation foundation-down ENV=$(ENV)

foundation-status:
	$(MAKE) -C foundation foundation-status ENV=$(ENV)

# --- Cluster ---
cluster-up:
	$(MAKE) -C cluster cluster-up ENV=$(ENV) CLUSTER=$(CLUSTER)

cluster-down:
	$(MAKE) -C cluster cluster-down ENV=$(ENV) CLUSTER=$(CLUSTER)

cluster-status:
	$(MAKE) -C cluster cluster-status ENV=$(ENV) CLUSTER=$(CLUSTER)

cluster-config:
	$(MAKE) -C cluster cluster-config ENV=$(ENV) CLUSTER=$(CLUSTER)

# --- Platform ---
# Platform Makefile relies on current kubectl context.
# We map 'up' to 'deploy' and 'down' to 'destroy' for consistency.
platform-up:
	@echo "==> Deploying Platform Layer (Context: $$(kubectl config current-context))"
	$(MAKE) -C platform deploy

platform-down:
	@echo "==> Destroying Platform Layer"
	$(MAKE) -C platform destroy

platform-status:
	$(MAKE) -C platform status

# ==============================================================================
# Documentation (Root Level)
# ==============================================================================

docs: docs-serve

docs-serve:
	uv run --group docs mkdocs serve

docs-build:
	uv run --group docs mkdocs build