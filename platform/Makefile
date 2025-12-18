# Platform Makefile - Makefile-first Bootstrap
# ============================================
# Deploys platform components in numbered layers using helm/kubectl.
# Run from: /platform directory
#
# Usage:
#   make env                 # Auto-discover and export all variables
#   make deploy              # Deploy all layers in order
#   make deploy-XX           # Deploy specific layer (e.g., deploy-01)
#   make destroy             # Tear down all layers in reverse order
#   make status              # Show deployment status
#
# Quick start:
#   eval $(make env)         # Load all variables from AWS
#   make deploy              # Deploy everything

SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

# ============================================================================
# Auto-Discovery from AWS/kubectl
# ============================================================================

# Discover cluster name from current kubectl context
CLUSTER_NAME ?= $(shell kubectl config current-context 2>/dev/null | sed 's/.*\///' | sed 's/arn:aws:eks:[^:]*:[^:]*:cluster\///')
AWS_REGION ?= $(shell aws configure get region 2>/dev/null || echo "us-west-2")

# Discover from EKS API (requires CLUSTER_NAME)
CLUSTER_ENDPOINT ?= $(shell aws eks describe-cluster --name $(CLUSTER_NAME) --query 'cluster.endpoint' --output text 2>/dev/null)
VPC_ID ?= $(shell aws eks describe-cluster --name $(CLUSTER_NAME) --query 'cluster.resourcesVpcConfig.vpcId' --output text 2>/dev/null)

# Discover SQS queues by naming convention
KARPENTER_QUEUE ?= $(shell aws sqs list-queues --queue-name-prefix $(CLUSTER_NAME) --query 'QueueUrls[?contains(@, `karpenter`)] | [0]' --output text 2>/dev/null)
NTH_QUEUE ?= $(shell aws sqs list-queues --queue-name-prefix $(CLUSTER_NAME) --query 'QueueUrls[?contains(@, `nth`) || contains(@, `termination`)] | [0]' --output text 2>/dev/null)

# Discover IRSA roles by naming convention: {cluster-name}-{component}
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null)
ROLE_PREFIX ?= $(CLUSTER_NAME)

EBS_CSI_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-ebs-csi --query 'Role.Arn' --output text 2>/dev/null || true)
EFS_CSI_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-efs-csi --query 'Role.Arn' --output text 2>/dev/null || true)
FSX_CSI_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-fsx-csi --query 'Role.Arn' --output text 2>/dev/null || true)
LB_CONTROLLER_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-aws-load-balancer-controller --query 'Role.Arn' --output text 2>/dev/null || true)
EXTERNAL_DNS_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-external-dns --query 'Role.Arn' --output text 2>/dev/null || true)
FLUENT_BIT_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-fluent-bit --query 'Role.Arn' --output text 2>/dev/null || true)
KARPENTER_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-karpenter --query 'Role.Arn' --output text 2>/dev/null || true)
KEDA_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-keda --query 'Role.Arn' --output text 2>/dev/null || true)
NTH_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-aws-node-termination-handler --query 'Role.Arn' --output text 2>/dev/null || true)
K8SGPT_ROLE_ARN ?= $(shell aws iam get-role --role-name $(ROLE_PREFIX)-k8sgpt --query 'Role.Arn' --output text 2>/dev/null || true)

# Helm repos
HELM_REPOS := \
	eks=https://aws.github.io/eks-charts \
	ebs-csi=https://kubernetes-sigs.github.io/aws-ebs-csi-driver \
	efs-csi=https://kubernetes-sigs.github.io/aws-efs-csi-driver \
	fsx-csi=https://kubernetes-sigs.github.io/aws-fsx-csi-driver \
	secrets-store=https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts \
	secrets-store-aws=https://aws.github.io/secrets-store-csi-driver-provider-aws \
	prometheus=https://prometheus-community.github.io/helm-charts \
	fluent=https://fluent.github.io/helm-charts \
	kyverno=https://kyverno.github.io/kyverno \
	keda=https://kedacore.github.io/charts \
	external-dns=https://kubernetes-sigs.github.io/external-dns \
	nvidia=https://nvidia.github.io/dcgm-exporter/helm-charts \
	k8sgpt=https://charts.k8sgpt.ai

# Chart versions
VPC_CNI_VERSION := 1.18.2
EBS_CSI_VERSION := 2.32.0
EFS_CSI_VERSION := 2.5.5
FSX_CSI_VERSION := 1.6.1
SECRETS_STORE_VERSION := 1.4.5
SECRETS_STORE_AWS_VERSION := 0.3.9
LB_CONTROLLER_VERSION := 1.9.2
EXTERNAL_DNS_VERSION := 1.15.0
PROMETHEUS_VERSION := 61.2.0
FLUENT_BIT_VERSION := 0.46.6
KYVERNO_VERSION := 3.2.7
KARPENTER_VERSION := 1.2.0
KEDA_VERSION := 2.14.0
NTH_VERSION := 0.21.0
DCGM_VERSION := 3.4.2
K8SGPT_VERSION := 0.2.3

# ============================================================================
# Environment Discovery Targets
# ============================================================================

.PHONY: env
env:
	@echo "# Platform environment (auto-discovered from AWS)"
	@echo "# Usage: eval \$$(make env)"
	@echo ""
	@echo "export CLUSTER_NAME=\"$(CLUSTER_NAME)\""
	@echo "export AWS_REGION=\"$(AWS_REGION)\""
	@echo "export CLUSTER_ENDPOINT=\"$(CLUSTER_ENDPOINT)\""
	@echo "export VPC_ID=\"$(VPC_ID)\""
	@echo ""
	@echo "# SQS Queues"
	@echo "export KARPENTER_QUEUE=\"$(KARPENTER_QUEUE)\""
	@echo "export NTH_QUEUE=\"$(NTH_QUEUE)\""
	@echo ""
	@echo "# IRSA Role ARNs"
	@echo "export EBS_CSI_ROLE_ARN=\"$(EBS_CSI_ROLE_ARN)\""
	@echo "export EFS_CSI_ROLE_ARN=\"$(EFS_CSI_ROLE_ARN)\""
	@echo "export FSX_CSI_ROLE_ARN=\"$(FSX_CSI_ROLE_ARN)\""
	@echo "export LB_CONTROLLER_ROLE_ARN=\"$(LB_CONTROLLER_ROLE_ARN)\""
	@echo "export EXTERNAL_DNS_ROLE_ARN=\"$(EXTERNAL_DNS_ROLE_ARN)\""
	@echo "export FLUENT_BIT_ROLE_ARN=\"$(FLUENT_BIT_ROLE_ARN)\""
	@echo "export KARPENTER_ROLE_ARN=\"$(KARPENTER_ROLE_ARN)\""
	@echo "export KEDA_ROLE_ARN=\"$(KEDA_ROLE_ARN)\""
	@echo "export NTH_ROLE_ARN=\"$(NTH_ROLE_ARN)\""
	@echo "export K8SGPT_ROLE_ARN=\"$(K8SGPT_ROLE_ARN)\""

.PHONY: env-file
env-file:
	@echo "Writing .env file..."
	@cat > .env <<-'ENVFILE'
	# Platform environment (auto-discovered from AWS)
	# Source with: source .env
	CLUSTER_NAME="$(CLUSTER_NAME)"
	AWS_REGION="$(AWS_REGION)"
	CLUSTER_ENDPOINT="$(CLUSTER_ENDPOINT)"
	VPC_ID="$(VPC_ID)"
	KARPENTER_QUEUE="$(KARPENTER_QUEUE)"
	NTH_QUEUE="$(NTH_QUEUE)"
	EBS_CSI_ROLE_ARN="$(EBS_CSI_ROLE_ARN)"
	EFS_CSI_ROLE_ARN="$(EFS_CSI_ROLE_ARN)"
	FSX_CSI_ROLE_ARN="$(FSX_CSI_ROLE_ARN)"
	LB_CONTROLLER_ROLE_ARN="$(LB_CONTROLLER_ROLE_ARN)"
	EXTERNAL_DNS_ROLE_ARN="$(EXTERNAL_DNS_ROLE_ARN)"
	FLUENT_BIT_ROLE_ARN="$(FLUENT_BIT_ROLE_ARN)"
	KARPENTER_ROLE_ARN="$(KARPENTER_ROLE_ARN)"
	KEDA_ROLE_ARN="$(KEDA_ROLE_ARN)"
	NTH_ROLE_ARN="$(NTH_ROLE_ARN)"
	K8SGPT_ROLE_ARN="$(K8SGPT_ROLE_ARN)"
	ENVFILE
	@echo "✅ Written to .env - run 'source .env' to load"

.PHONY: env-check
env-check:
	@echo "=== Environment Check ==="
	@echo ""
	@printf "%-30s %s\n" "Variable" "Value"
	@printf "%-30s %s\n" "--------" "-----"
	@printf "%-30s %s\n" "CLUSTER_NAME" "$(CLUSTER_NAME)"
	@printf "%-30s %s\n" "AWS_REGION" "$(AWS_REGION)"
	@printf "%-30s %s\n" "CLUSTER_ENDPOINT" "$(if $(CLUSTER_ENDPOINT),$(shell echo $(CLUSTER_ENDPOINT) | cut -c1-50)...,❌ NOT SET)"
	@printf "%-30s %s\n" "VPC_ID" "$(if $(VPC_ID),$(VPC_ID),❌ NOT SET)"
	@printf "%-30s %s\n" "KARPENTER_QUEUE" "$(if $(KARPENTER_QUEUE),✅ Found,⚠️  Not found)"
	@printf "%-30s %s\n" "NTH_QUEUE" "$(if $(NTH_QUEUE),✅ Found,⚠️  Not found)"
	@echo ""
	@echo "=== IRSA Roles ==="
	@printf "%-30s %s\n" "EBS_CSI_ROLE_ARN" "$(if $(EBS_CSI_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "EFS_CSI_ROLE_ARN" "$(if $(EFS_CSI_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "FSX_CSI_ROLE_ARN" "$(if $(FSX_CSI_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "LB_CONTROLLER_ROLE_ARN" "$(if $(LB_CONTROLLER_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "EXTERNAL_DNS_ROLE_ARN" "$(if $(EXTERNAL_DNS_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "FLUENT_BIT_ROLE_ARN" "$(if $(FLUENT_BIT_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "KARPENTER_ROLE_ARN" "$(if $(KARPENTER_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "KEDA_ROLE_ARN" "$(if $(KEDA_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "NTH_ROLE_ARN" "$(if $(NTH_ROLE_ARN),✅,❌)"
	@printf "%-30s %s\n" "K8SGPT_ROLE_ARN" "$(if $(K8SGPT_ROLE_ARN),✅,❌)"

# ============================================================================
# Main Targets
# ============================================================================

.PHONY: prerequisites
prerequisites:
	@echo "🔍 Checking infrastructure prerequisites..."
	@echo "  - Checking ECR repository 'skyhook-docs'..."
	@aws ecr describe-repositories --repository-names skyhook-docs >/dev/null 2>&1 || \
		(echo "    Creating repo..." && aws ecr create-repository --repository-name skyhook-docs >/dev/null)
	@echo "  - Checking Security Group tags for Karpenter..."
	@if [ -z "$$(aws ec2 describe-security-groups --filters Name=tag:karpenter.sh/discovery,Values=$(CLUSTER_NAME) --query 'SecurityGroups[].GroupId' --output text)" ]; then \
		echo "    ⚠️  Warning: No Security Group found with tag 'karpenter.sh/discovery: $(CLUSTER_NAME)'"; \
		echo "    Attempting to auto-tag ClusterSharedNodeSecurityGroup..."; \
		SG_ID=$$(aws ec2 describe-security-groups --filters Name=tag:alpha.eksctl.io/cluster-name,Values=$(CLUSTER_NAME) Name=tag:aws:cloudformation:logical-id,Values=ClusterSharedNodeSecurityGroup --query 'SecurityGroups[0].GroupId' --output text); \
		if [ -n "$$SG_ID" ] && [ "$$SG_ID" != "None" ]; then \
			aws ec2 create-tags --resources $$SG_ID --tags Key=karpenter.sh/discovery,Value=$(CLUSTER_NAME); \
			echo "    ✅ Tagged $$SG_ID"; \
		else \
			echo "    ❌ Could not find SG to tag. Karpenter may fail."; \
		fi \
	else \
		echo "    ✅ Karpenter discovery tag found"; \
	fi

.PHONY: deploy
deploy: prerequisites env-check setup-repos deploy-00 deploy-01 deploy-02 deploy-03 deploy-04 deploy-05 deploy-06 deploy-07 deploy-08 deploy-09
	@echo "✅ Platform deployment complete"

.PHONY: destroy
destroy: destroy-09 destroy-08 destroy-07 destroy-06 destroy-05 destroy-04 destroy-03 destroy-02 destroy-01 destroy-00
	@echo "✅ Platform teardown complete"

.PHONY: status
status:
	@echo "=== Platform Status ==="
	@echo ""
	@echo "Namespaces:"
	@kubectl get ns -l app.kubernetes.io/managed-by=Helm 2>/dev/null || true
	@echo ""
	@echo "Helm Releases:"
	@helm list -A 2>/dev/null || echo "No releases found"
	@echo ""
	@echo "Karpenter NodePools:"
	@kubectl get nodepools.karpenter.sh 2>/dev/null || echo "Not installed"
	@echo ""
	@echo "Kyverno Policies:"
	@kubectl get clusterpolicies 2>/dev/null || echo "Not installed"

.PHONY: setup-repos
setup-repos:
	@echo "📦 Adding Helm repositories..."
	@for repo in $(HELM_REPOS); do \
		name=$${repo%%=*}; \
		url=$${repo#*=}; \
		helm repo add $$name $$url 2>/dev/null || true; \
	done
	@helm repo add karpenter oci://public.ecr.aws/karpenter 2>/dev/null || true
	@helm repo update

# ============================================================================
# Layer 00: Namespaces
# ============================================================================

.PHONY: deploy-00
deploy-00:
	@echo "🏗️  [00] Deploying namespaces..."
	kubectl apply -k 00-namespaces/
	@echo "✅ [00] Namespaces deployed"

.PHONY: destroy-00
destroy-00:
	@echo "🗑️  [00] Removing namespaces..."
	kubectl delete -k 00-namespaces/ --ignore-not-found
	@echo "✅ [00] Namespaces removed"

# ============================================================================
# Layer 01: Storage (CSI Drivers)
# ============================================================================

.PHONY: deploy-01
# deploy-01: deploy-01-ebs deploy-01-efs deploy-01-fsx
# Skipping EBS and FSx as they are EKS Managed Add-ons
deploy-01: deploy-01-efs
	@echo "✅ [01] Storage layer deployed"

.PHONY: deploy-01-ebs
deploy-01-ebs:
	@echo "🏗️  [01] Deploying EBS CSI driver..."
	helm upgrade --install aws-ebs-csi-driver ebs-csi/aws-ebs-csi-driver \
		--namespace kube-system \
		--version $(EBS_CSI_VERSION) \
		--values 01-storage/ebs-csi-values.yaml \
		$${EBS_CSI_ROLE_ARN:+--set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$EBS_CSI_ROLE_ARN} \
		--wait

.PHONY: deploy-01-efs
deploy-01-efs:
	@echo "🏗️  [01] Deploying EFS CSI driver..."
	helm upgrade --install aws-efs-csi-driver efs-csi/aws-efs-csi-driver \
		--namespace kube-system \
		--version $(EFS_CSI_VERSION) \
		--values 01-storage/efs-csi-values.yaml \
		$${EFS_CSI_ROLE_ARN:+--set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$EFS_CSI_ROLE_ARN} \
		--wait

.PHONY: deploy-01-fsx
deploy-01-fsx:
	@echo "🏗️  [01] Deploying FSx CSI driver..."
	helm upgrade --install aws-fsx-csi-driver fsx-csi/aws-fsx-csi-driver \
		--namespace kube-system \
		--version $(FSX_CSI_VERSION) \
		--values 01-storage/fsx-csi-values.yaml \
		$${FSX_CSI_ROLE_ARN:+--set controller.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$FSX_CSI_ROLE_ARN} \
		--wait

.PHONY: destroy-01
destroy-01:
	@echo "🗑️  [01] Removing storage drivers..."
	helm uninstall aws-fsx-csi-driver -n kube-system --ignore-not-found || true
	helm uninstall aws-efs-csi-driver -n kube-system --ignore-not-found || true
	helm uninstall aws-ebs-csi-driver -n kube-system --ignore-not-found || true
	@echo "✅ [01] Storage layer removed"

# ============================================================================
# Layer 02: Networking (CNI, LB Controller, External DNS)
# ============================================================================

.PHONY: deploy-02
# deploy-02: deploy-02-cni deploy-02-lb deploy-02-dns
# Skipping VPC CNI as it is an EKS Managed Add-on
deploy-02: deploy-02-lb deploy-02-dns
	@echo "✅ [02] Networking layer deployed"

.PHONY: deploy-02-cni
deploy-02-cni:
	@echo "🏗️  [02] Deploying VPC CNI..."
	helm upgrade --install aws-vpc-cni eks/aws-vpc-cni \
		--namespace kube-system \
		--version $(VPC_CNI_VERSION) \
		--values 02-networking/vpc-cni-values.yaml \
		--wait

.PHONY: deploy-02-lb
deploy-02-lb:
	@echo "🏗️  [02] Deploying AWS Load Balancer Controller..."
	helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
		--namespace kube-system \
		--version $(LB_CONTROLLER_VERSION) \
		--values 02-networking/lb-controller-values.yaml \
		--set clusterName=$${CLUSTER_NAME:?CLUSTER_NAME required} \
		$${VPC_ID:+--set vpcId=$$VPC_ID} \
		$${AWS_REGION:+--set region=$$AWS_REGION} \
		$${LB_CONTROLLER_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$LB_CONTROLLER_ROLE_ARN} \
		--wait

.PHONY: deploy-02-dns
deploy-02-dns:
	@echo "🏗️  [02] Deploying External DNS..."
	helm upgrade --install external-dns external-dns/external-dns \
		--namespace external-dns \
		--create-namespace \
		--version $(EXTERNAL_DNS_VERSION) \
		--values 02-networking/external-dns-values.yaml \
		$${EXTERNAL_DNS_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$EXTERNAL_DNS_ROLE_ARN} \
		--wait

.PHONY: destroy-02
destroy-02:
	@echo "🗑️  [02] Removing networking components..."
	helm uninstall external-dns -n external-dns --ignore-not-found || true
	helm uninstall aws-load-balancer-controller -n kube-system --ignore-not-found || true
	# Note: VPC CNI should typically not be uninstalled
	@echo "✅ [02] Networking layer removed (VPC CNI retained)"

# ============================================================================
# Layer 03: Secrets (Secrets Store CSI)
# ============================================================================

.PHONY: deploy-03
deploy-03: deploy-03-csi deploy-03-provider
	@echo "✅ [03] Secrets layer deployed"

.PHONY: deploy-03-csi
deploy-03-csi:
	@echo "🏗️  [03] Deploying Secrets Store CSI driver..."
	helm upgrade --install secrets-store-csi-driver secrets-store/secrets-store-csi-driver \
		--namespace kube-system \
		--version $(SECRETS_STORE_VERSION) \
		--values 03-secrets/secrets-store-csi-values.yaml \
		--wait

.PHONY: deploy-03-provider
deploy-03-provider:
	@echo "🏗️  [03] Deploying AWS Secrets Manager provider..."
	helm upgrade --install secrets-store-csi-driver-provider-aws secrets-store-aws/secrets-store-csi-driver-provider-aws \
		--namespace kube-system \
		--version $(SECRETS_STORE_AWS_VERSION) \
		--values 03-secrets/secrets-store-provider-aws-values.yaml \
		--wait

.PHONY: destroy-03
destroy-03:
	@echo "🗑️  [03] Removing secrets components..."
	helm uninstall secrets-store-csi-driver-provider-aws -n kube-system --ignore-not-found || true
	helm uninstall secrets-store-csi-driver -n kube-system --ignore-not-found || true
	@echo "✅ [03] Secrets layer removed"

# ============================================================================
# Layer 04: Observability (Prometheus Stack, Fluent Bit)
# ============================================================================

.PHONY: deploy-04
deploy-04: deploy-04-prometheus deploy-04-logging
	@echo "✅ [04] Observability layer deployed"

.PHONY: deploy-04-prometheus
deploy-04-prometheus:
	@echo "🏗️  [04] Deploying Prometheus stack..."
	helm upgrade --install kube-prometheus-stack prometheus/kube-prometheus-stack \
		--namespace observability \
		--create-namespace \
		--version $(PROMETHEUS_VERSION) \
		--values 04-observability/prometheus-stack-values.yaml \
		--wait --timeout 10m

.PHONY: deploy-04-logging
deploy-04-logging:
	@echo "🏗️  [04] Deploying Fluent Bit..."
	helm upgrade --install fluent-bit fluent/fluent-bit \
		--namespace logging \
		--create-namespace \
		--version $(FLUENT_BIT_VERSION) \
		--values 04-observability/fluent-bit-values.yaml \
		--set env[0].value=$${AWS_REGION:-us-west-2} \
		--set env[1].value=$${CLUSTER_NAME:-unknown} \
		--set env[2].value=$${ENVIRONMENT:-dev} \
		$${FLUENT_BIT_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$FLUENT_BIT_ROLE_ARN} \
		--wait

.PHONY: destroy-04
destroy-04:
	@echo "🗑️  [04] Removing observability components..."
	helm uninstall fluent-bit -n logging --ignore-not-found || true
	helm uninstall kube-prometheus-stack -n observability --ignore-not-found || true
	@echo "✅ [04] Observability layer removed"

# ============================================================================
# Layer 05: Policy (Kyverno + ClusterPolicies)
# ============================================================================

.PHONY: deploy-05
deploy-05: deploy-05-kyverno deploy-05-policies
	@echo "✅ [05] Policy layer deployed"

.PHONY: deploy-05-kyverno
deploy-05-kyverno:
	@echo "🏗️  [05] Deploying Kyverno..."
	helm upgrade --install kyverno kyverno/kyverno \
		--namespace kyverno \
		--create-namespace \
		--version $(KYVERNO_VERSION) \
		--values 05-policy/kyverno-values.yaml \
		--wait --timeout 5m

.PHONY: deploy-05-policies
deploy-05-policies:
	@echo "🏗️  [05] Applying Kyverno policies..."
	@sleep 10  # Wait for CRDs to be available
	kubectl apply -k 05-policy/policies/

.PHONY: destroy-05
destroy-05:
	@echo "🗑️  [05] Removing policy components..."
	kubectl delete -k 05-policy/policies/ --ignore-not-found || true
	helm uninstall kyverno -n kyverno --ignore-not-found || true
	@echo "✅ [05] Policy layer removed"

# ============================================================================
# Layer 06: Karpenter
# ============================================================================

.PHONY: deploy-06
deploy-06: deploy-06-karpenter deploy-06-resources
	@echo "✅ [06] Karpenter layer deployed"

.PHONY: deploy-06-karpenter
deploy-06-karpenter:
	@echo "🏗️  [06] Deploying Karpenter..."
	helm upgrade --install karpenter oci://public.ecr.aws/karpenter/karpenter \
		--namespace karpenter \
		--create-namespace \
		--version $(KARPENTER_VERSION) \
		--values 06-karpenter/karpenter-values.yaml \
		--set settings.clusterName=$${CLUSTER_NAME:?CLUSTER_NAME required} \
		--set settings.clusterEndpoint=$${CLUSTER_ENDPOINT:?CLUSTER_ENDPOINT required} \
		$${KARPENTER_QUEUE:+--set settings.interruptionQueue=$$KARPENTER_QUEUE} \
		$${KARPENTER_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$KARPENTER_ROLE_ARN} \
		--wait --timeout 5m

.PHONY: deploy-06-resources
deploy-06-resources:
	@echo "🏗️  [06] Applying Karpenter resources..."
	@sleep 10  # Wait for CRDs to be available
	@echo "    - Generating ec2nodeclasses.yaml from template..."
	@export CLUSTER_NAME=$(CLUSTER_NAME); \
	envsubst < 06-karpenter/manifests/ec2nodeclasses.tpl > 06-karpenter/manifests/ec2nodeclasses.yaml
	kubectl apply -k 06-karpenter/manifests/

.PHONY: destroy-06
destroy-06:
	@echo "🗑️  [06] Removing Karpenter components..."
	kubectl delete -k 06-karpenter/manifests/ --ignore-not-found || true
	helm uninstall karpenter -n karpenter --ignore-not-found || true
	@echo "✅ [06] Karpenter layer removed"

# ============================================================================
# Layer 07: Scaling (KEDA, NTH)
# ============================================================================

.PHONY: deploy-07
deploy-07: deploy-07-keda deploy-07-nth deploy-07-resources
	@echo "✅ [07] Scaling layer deployed"

.PHONY: deploy-07-keda
deploy-07-keda:
	@echo "🏗️  [07] Deploying KEDA..."
	helm upgrade --install keda keda/keda \
		--namespace keda \
		--create-namespace \
		--version $(KEDA_VERSION) \
		--values 07-scaling/keda-values.yaml \
		$${KEDA_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$KEDA_ROLE_ARN} \
		--wait

.PHONY: deploy-07-nth
deploy-07-nth:
	@echo "🏗️  [07] Deploying Node Termination Handler..."
	helm upgrade --install aws-node-termination-handler eks/aws-node-termination-handler \
		--namespace kube-system \
		--version $(NTH_VERSION) \
		--values 07-scaling/nth-values.yaml \
		$${NTH_QUEUE:+--set queueURL=$$NTH_QUEUE} \
		$${NTH_ROLE_ARN:+--set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$NTH_ROLE_ARN} \
		--wait

.PHONY: deploy-07-resources
deploy-07-resources:
	@echo "🏗️  [07] Applying scaling resources..."
	@sleep 5  # Wait for CRDs
	kubectl apply -k 07-scaling/manifests/

.PHONY: destroy-07
destroy-07:
	@echo "🗑️  [07] Removing scaling components..."
	kubectl delete -k 07-scaling/manifests/ --ignore-not-found || true
	helm uninstall aws-node-termination-handler -n kube-system --ignore-not-found || true
	helm uninstall keda -n keda --ignore-not-found || true
	@echo "✅ [07] Scaling layer removed"

# ============================================================================
# Layer 08: Apps (DCGM Exporter, K8sGPT)
# ============================================================================

.PHONY: deploy-08
deploy-08: deploy-08-dcgm deploy-08-k8sgpt deploy-08-resources
	@echo "✅ [08] Apps layer deployed"

.PHONY: deploy-08-dcgm
deploy-08-dcgm:
	@echo "🏗️  [08] Deploying DCGM Exporter..."
	helm upgrade --install dcgm-exporter nvidia/dcgm-exporter \
		--namespace observability \
		--version $(DCGM_VERSION) \
		--values 08-apps/dcgm-exporter-values.yaml \
		--wait || true  # May fail if no GPU nodes

.PHONY: deploy-08-k8sgpt
deploy-08-k8sgpt:
	@echo "🏗️  [08] Deploying K8sGPT Operator..."
	helm upgrade --install k8sgpt-operator k8sgpt/k8sgpt-operator \
		--namespace k8sgpt-operator-system \
		--version $(K8SGPT_VERSION) \
		--values 08-apps/k8sgpt-operator-values.yaml \
		$${K8SGPT_ROLE_ARN:+--set controllerManager.manager.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=$$K8SGPT_ROLE_ARN} \
		--wait

.PHONY: deploy-08-resources
deploy-08-resources:
	@echo "🏗️  [08] Applying app resources..."
	@sleep 5  # Wait for CRDs
	kubectl apply -k 08-apps/manifests/

.PHONY: destroy-08
destroy-08:
	@echo "🗑️  [08] Removing app components..."
	kubectl delete -k 08-apps/manifests/ --ignore-not-found || true
	helm uninstall k8sgpt-operator -n k8sgpt-operator-system --ignore-not-found || true
	helm uninstall dcgm-exporter -n observability --ignore-not-found || true
	@echo "✅ [08] Apps layer removed"

# ============================================================================
# Layer 09: Documentation
# ============================================================================

# Image configuration for docs
DOCS_IMAGE ?= skyhook-docs
DOCS_TAG ?= latest
DOCS_REGISTRY ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

.PHONY: deploy-09
deploy-09: deploy-09-build deploy-09-push deploy-09-resources
	@echo "✅ [09] Documentation layer deployed"

.PHONY: deploy-09-build
deploy-09-build:
	@echo "🏗️  [09] Building docs image..."
	docker build --platform linux/amd64 -f ../Dockerfile.docs -t $(DOCS_IMAGE):$(DOCS_TAG) ..

.PHONY: deploy-09-push
deploy-09-push:
	@echo "🏗️  [09] Pushing docs image to ECR..."
	@if [ -n "$(DOCS_REGISTRY)" ] && [ "$(DOCS_REGISTRY)" != ".dkr.ecr..amazonaws.com" ]; then \
		aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(DOCS_REGISTRY); \
		docker tag $(DOCS_IMAGE):$(DOCS_TAG) $(DOCS_REGISTRY)/$(DOCS_IMAGE):$(DOCS_TAG); \
		docker push $(DOCS_REGISTRY)/$(DOCS_IMAGE):$(DOCS_TAG); \
	else \
		echo "⚠️  Skipping push - no ECR registry configured"; \
	fi

.PHONY: deploy-09-resources
deploy-09-resources:
	@echo "🏗️  [09] Deploying docs resources..."
	@if [ -n "$(DOCS_REGISTRY)" ] && [ "$(DOCS_REGISTRY)" != ".dkr.ecr..amazonaws.com" ]; then \
		kubectl apply -k 09-docs/manifests/; \
		kubectl set image deployment/skyhook-docs docs=$(DOCS_REGISTRY)/$(DOCS_IMAGE):$(DOCS_TAG) -n docs; \
	else \
		kubectl apply -k 09-docs/manifests/; \
		echo "⚠️  Using local image - ensure imagePullPolicy is Never/IfNotPresent"; \
	fi

.PHONY: deploy-09-local
deploy-09-local: deploy-09-build
	@echo "🏗️  [09] Deploying docs locally (no ECR push)..."
	kubectl apply -k 09-docs/manifests/
	@echo "✅ [09] Documentation deployed with local image"

.PHONY: destroy-09
destroy-09:
	@echo "🗑️  [09] Removing documentation..."
	kubectl delete -k 09-docs/manifests/ --ignore-not-found || true
	@echo "✅ [09] Documentation layer removed"

# ============================================================================
# Helper Targets
# ============================================================================

.PHONY: help
help:
	@echo "Platform Makefile - Makefile-first Bootstrap"
	@echo ""
	@echo "Environment (auto-discovered from AWS):"
	@echo "  make env             Print export statements for all variables"
	@echo "  make env-file        Write .env file for sourcing"
	@echo "  make env-check       Show discovery status with ✅/❌"
	@echo ""
	@echo "Quick Start:"
	@echo "  eval \$$(make env)    Load variables into current shell"
	@echo "  make deploy          Deploy all layers"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy          Deploy all layers (00-09)"
	@echo "  make deploy-XX       Deploy specific layer (00-09)"
	@echo "  make destroy         Tear down all layers"
	@echo "  make status          Show deployment status"
	@echo ""
	@echo "Individual Components:"
	@echo "  make deploy-01-ebs   Deploy EBS CSI only"
	@echo "  make deploy-02-lb    Deploy Load Balancer Controller only"
	@echo "  make deploy-09-local Deploy docs locally (no ECR push)"
	@echo "  etc."
	@echo ""
	@echo "Documentation:"
	@echo "  make deploy-09       Build, push to ECR, and deploy docs"
	@echo "  make deploy-09-local Build and deploy docs (no ECR push)"
	@echo "  Endpoint: http://docs.skyhook.internal"
	@echo ""
	@echo "Variables are auto-discovered from:"
	@echo "  - kubectl context → CLUSTER_NAME"
	@echo "  - aws configure   → AWS_REGION"
	@echo "  - aws eks         → CLUSTER_ENDPOINT, VPC_ID"
	@echo "  - aws sqs         → KARPENTER_QUEUE, NTH_QUEUE"
	@echo "  - aws iam         → All *_ROLE_ARN (by naming convention)"

.PHONY: validate
validate:
	@echo "Validating manifests..."
	@for dir in */manifests 05-policy/policies; do \
		if [ -d "$$dir" ]; then \
			echo "  Checking $$dir..."; \
			kubectl kustomize $$dir > /dev/null && echo "    ✅ Valid" || echo "    ❌ Invalid"; \
		fi \
	done

