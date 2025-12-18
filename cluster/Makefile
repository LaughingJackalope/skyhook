# ==============================================================================
# Makefile for Skyhook Cluster Releases
# ==============================================================================
#
# Cluster releases are ephemeral EKS clusters built on top of a foundation.
# They can be created, validated, promoted, and destroyed independently.
#
# Usage:
#   make cluster-up ENV=accel-usw2 CLUSTER=v42
#   make cluster-status ENV=accel-usw2 CLUSTER=v42
#   make cluster-down ENV=accel-usw2 CLUSTER=v42

# Required parameters
ENV ?=
CLUSTER ?=

# Derived values
CLUSTER_NAME = skyhook-$(ENV)-$(CLUSTER)
EKSCTL_TEMPLATE = eksctl-template.yaml
GENERATED_DIR = .generated
GENERATED_CONFIG = $(GENERATED_DIR)/$(CLUSTER_NAME).yaml
IAM_TEMPLATE = iam-cluster.yaml
IAM_STACK_NAME = $(CLUSTER_NAME)-iam
REGION ?= us-west-2

# ==============================================================================
# Validation
# ==============================================================================
.PHONY: _check-params _fetch-foundation

_check-params:
ifndef ENV
	$(error ENV is required. Usage: make <target> ENV=<environment> CLUSTER=<release>)
endif
ifndef CLUSTER
	$(error CLUSTER is required. Usage: make <target> ENV=<environment> CLUSTER=<release>)
endif

# Fetch foundation parameters from SSM
_fetch-foundation: _check-params
	$(eval VPC_ID := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/vpc-id --query Parameter.Value --output text --region $(REGION)))
	$(eval SYSTEM_SUBNETS := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/system-subnet-ids --query Parameter.Value --output text --region $(REGION)))
	$(eval SYSTEM_SUBNET_1 := $(shell echo $(SYSTEM_SUBNETS) | cut -d',' -f1))
	$(eval SYSTEM_SUBNET_2 := $(shell echo $(SYSTEM_SUBNETS) | cut -d',' -f2))
	$(eval SYSTEM_SUBNET_3 := $(shell echo $(SYSTEM_SUBNETS) | cut -d',' -f3))
	$(eval PRIMARY_AZ := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/primary-az --query Parameter.Value --output text --region $(REGION)))
	$(eval SECONDARY_AZ := $(shell aws ec2 describe-subnets --subnet-ids $(SYSTEM_SUBNET_2) --query 'Subnets[0].AvailabilityZone' --output text --region $(REGION)))
	$(eval TERTIARY_AZ := $(shell aws ec2 describe-subnets --subnet-ids $(SYSTEM_SUBNET_3) --query 'Subnets[0].AvailabilityZone' --output text --region $(REGION)))
	@echo "==> Foundation parameters fetched for $(ENV)"
	@echo "    VPC: $(VPC_ID)"
	@echo "    System Subnets: $(SYSTEM_SUBNETS)"

# ==============================================================================
# Cluster Lifecycle
# ==============================================================================
.PHONY: cluster-up cluster-down cluster-status cluster-config cluster-list

# Generate cluster config from template
cluster-config: _fetch-foundation
	@echo "==> Generating cluster config: $(GENERATED_CONFIG)"
	$(eval ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text))
	@mkdir -p $(GENERATED_DIR)
	@CLUSTER_NAME=$(CLUSTER_NAME) \
		ENV=$(ENV) \
		ACCOUNT_ID=$(ACCOUNT_ID) \
		VPC_ID=$(VPC_ID) \
		SYSTEM_SUBNET_1=$(SYSTEM_SUBNET_1) \
		SYSTEM_SUBNET_2=$(SYSTEM_SUBNET_2) \
		SYSTEM_SUBNET_3=$(SYSTEM_SUBNET_3) \
		PRIMARY_AZ=$(PRIMARY_AZ) \
		SECONDARY_AZ=$(SECONDARY_AZ) \
		TERTIARY_AZ=$(TERTIARY_AZ) \
		SSH_PUBLIC_KEY_PATH=$(SSH_PUBLIC_KEY_PATH) \
		envsubst < $(EKSCTL_TEMPLATE) > $(GENERATED_CONFIG)
	@echo "==> Config written to $(GENERATED_CONFIG)"

# Create cluster and IAM resources
cluster-up: cluster-config _deploy-iam
	@echo "==> Creating EKS cluster: $(CLUSTER_NAME)"
	eksctl create cluster -f $(GENERATED_CONFIG)
	@echo "==> Cluster created!"
	@$(MAKE) _create-cluster-config ENV=$(ENV) CLUSTER=$(CLUSTER)
	@echo ""
	@echo "==> Cluster $(CLUSTER_NAME) is ready!"
	@echo "    kubectl context: $(CLUSTER_NAME)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Bootstrap Flux (this installs Flux and applies platform components): make flux-bootstrap ENV=$(ENV) CLUSTER=$(CLUSTER)"
	@echo "  2. Update IAM:    make iam-update ENV=$(ENV) CLUSTER=$(CLUSTER)"

# Show cluster status
cluster-status: _check-params
	@echo "==> Cluster Status: $(CLUSTER_NAME)"
	@eksctl get cluster --name $(CLUSTER_NAME) --region $(REGION) 2>/dev/null || echo "Cluster not found"
	@echo ""
	@echo "==> Node Groups:"
	@eksctl get nodegroup --cluster $(CLUSTER_NAME) --region $(REGION) 2>/dev/null || echo "No node groups"
	@echo ""
	@echo "==> IAM Stack:"
	@aws cloudformation describe-stacks --stack-name $(IAM_STACK_NAME) \
		--query 'Stacks[0].StackStatus' --output text --region $(REGION) 2>/dev/null || echo "IAM stack not found"

# Delete cluster
cluster-down: _check-params
	@echo "==> Deleting cluster: $(CLUSTER_NAME)"
	@echo "This will:"
	@echo "  1. Delete all Kubernetes resources"
	@echo "  2. Delete the EKS cluster"
	@echo "  3. Delete the IAM stack"
	@echo ""
	@read -p "Type '$(CLUSTER_NAME)' to confirm: " confirm && \
		[ "$$confirm" = "$(CLUSTER_NAME)" ] || (echo "Aborted." && exit 1)
	@echo "==> Draining Karpenter nodes..."
	$(eval KUBE_CONTEXT := $(shell kubectl config get-contexts -o name | grep $(CLUSTER_NAME) | head -n 1))
	-kubectl delete nodepools --all --context $(KUBE_CONTEXT)
	@echo "==> Deleting cluster..."
	-eksctl delete cluster --name $(CLUSTER_NAME) --region $(REGION) --wait
	@echo "==> Deleting IAM stack..."
	-aws cloudformation delete-stack --stack-name $(IAM_STACK_NAME) --region $(REGION)
	-aws cloudformation wait stack-delete-complete --stack-name $(IAM_STACK_NAME) --region $(REGION)
	@echo "==> Cluster $(CLUSTER_NAME) deleted."

# List all clusters in this environment
cluster-list: _check-params
	@echo "==> Clusters in environment $(ENV):"
	@eksctl get cluster --region $(REGION) 2>/dev/null | grep "skyhook-$(ENV)" || echo "No clusters found"

# ==============================================================================
# Cluster Config (ConfigMap for Flux variable substitution)
# ==============================================================================
.PHONY: _create-cluster-config cluster-config-update

_create-cluster-config: _check-params
	$(eval CLUSTER_ENDPOINT := $(shell aws eks describe-cluster --name $(CLUSTER_NAME) --query 'cluster.endpoint' --output text --region $(REGION)))
	$(eval ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text))
	$(eval FSX_DNS := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/fsx-dns-name --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval FSX_MOUNT := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/fsx-mount-name --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval HPC_SUBNETS := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/hpc-subnet-ids --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval PLACEMENT_GROUPS := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/placement-groups --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	# Fetch Role ARNs
	$(eval NTH_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/nth-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval FLB_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/fluent-bit-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval EDNS_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/external-dns-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval K8SGPT_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/k8sgpt-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval KEDA_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/keda-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval EBS_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/ebs-csi-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval EFS_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/efs-csi-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval FSX_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/fsx-csi-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval SS_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/secrets-store-csi-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))
	$(eval ALB_ROLE_ARN := $(shell aws ssm get-parameter --name /skyhook/$(ENV)/clusters/$(CLUSTER_NAME)/aws-lb-controller-role-arn --query Parameter.Value --output text --region $(REGION) 2>/dev/null || echo ""))

	@echo "==> Creating cluster-config ConfigMaps in flux-system namespace"
	@kubectl create namespace flux-system --dry-run=client -o yaml | kubectl apply -f -
	@# General cluster config
	@kubectl create configmap cluster-config \
		--namespace flux-system \
		--from-literal=CLUSTER_NAME=$(CLUSTER_NAME) \
		--from-literal=CLUSTER_ENDPOINT=$(CLUSTER_ENDPOINT) \
		--from-literal=ENVIRONMENT=$(ENV) \
		--from-literal=ACCOUNT_ID=$(ACCOUNT_ID) \
		--from-literal=REGION=$(REGION) \
		--from-literal=FSX_DNS_NAME=$(FSX_DNS) \
		--from-literal=FSX_MOUNT_NAME=$(FSX_MOUNT) \
		--from-literal=HPC_SUBNET_IDS=$(HPC_SUBNETS) \
		--from-literal=PLACEMENT_GROUPS=$(PLACEMENT_GROUPS) \
		--dry-run=client -o yaml | kubectl apply -f -
	@# Karpenter-specific values (YAML format for valuesFrom)
	@mkdir -p $(GENERATED_DIR)
	@echo 'settings:' > $(GENERATED_DIR)/karpenter-values.yaml
	@echo '  clusterName: $(CLUSTER_NAME)' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo '  clusterEndpoint: $(CLUSTER_ENDPOINT)' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo 'serviceAccount:' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo '  create: true' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo '  name: karpenter' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/karpenter-values.yaml
	@echo '    eks.amazonaws.com/role-arn: arn:aws:iam::$(ACCOUNT_ID):role/$(CLUSTER_NAME)-karpenter' >> $(GENERATED_DIR)/karpenter-values.yaml
	@kubectl create configmap karpenter-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/karpenter-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -
	
	@# Node Termination Handler values
	@echo 'serviceAccount:' > $(GENERATED_DIR)/nth-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/nth-values.yaml
	@echo '    eks.amazonaws.com/role-arn: $(NTH_ROLE_ARN)' >> $(GENERATED_DIR)/nth-values.yaml
	@kubectl create configmap nth-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/nth-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# Fluent Bit values
	@echo 'serviceAccount:' > $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '    eks.amazonaws.com/role-arn: $(FLB_ROLE_ARN)' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo 'env:' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '  - name: AWS_REGION' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '    value: $(REGION)' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '  - name: CLUSTER_NAME' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '    value: $(CLUSTER_NAME)' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '  - name: ENVIRONMENT' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@echo '    value: $(ENV)' >> $(GENERATED_DIR)/fluent-bit-values.yaml
	@kubectl create configmap fluent-bit-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/fluent-bit-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# External DNS values
	@echo 'serviceAccount:' > $(GENERATED_DIR)/external-dns-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/external-dns-values.yaml
	@echo '    eks.amazonaws.com/role-arn: $(EDNS_ROLE_ARN)' >> $(GENERATED_DIR)/external-dns-values.yaml
	@kubectl create configmap external-dns-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/external-dns-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# K8sGPT values
	@echo 'controllerManager:' > $(GENERATED_DIR)/k8sgpt-values.yaml
	@echo '  manager:' >> $(GENERATED_DIR)/k8sgpt-values.yaml
	@echo '    serviceAccount:' >> $(GENERATED_DIR)/k8sgpt-values.yaml
	@echo '      annotations:' >> $(GENERATED_DIR)/k8sgpt-values.yaml
	@echo '        eks.amazonaws.com/role-arn: $(K8SGPT_ROLE_ARN)' >> $(GENERATED_DIR)/k8sgpt-values.yaml
	@kubectl create configmap k8sgpt-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/k8sgpt-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# KEDA values
	@echo 'serviceAccount:' > $(GENERATED_DIR)/keda-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/keda-values.yaml
	@echo '    eks.amazonaws.com/role-arn: $(KEDA_ROLE_ARN)' >> $(GENERATED_DIR)/keda-values.yaml
	@kubectl create configmap keda-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/keda-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# EBS CSI values
	@echo 'controller:' > $(GENERATED_DIR)/ebs-csi-values.yaml
	@echo '  serviceAccount:' >> $(GENERATED_DIR)/ebs-csi-values.yaml
	@echo '    annotations:' >> $(GENERATED_DIR)/ebs-csi-values.yaml
	@echo '      eks.amazonaws.com/role-arn: $(EBS_ROLE_ARN)' >> $(GENERATED_DIR)/ebs-csi-values.yaml
	@kubectl create configmap ebs-csi-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/ebs-csi-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# EFS CSI values
	@echo 'controller:' > $(GENERATED_DIR)/efs-csi-values.yaml
	@echo '  serviceAccount:' >> $(GENERATED_DIR)/efs-csi-values.yaml
	@echo '    annotations:' >> $(GENERATED_DIR)/efs-csi-values.yaml
	@echo '      eks.amazonaws.com/role-arn: $(EFS_ROLE_ARN)' >> $(GENERATED_DIR)/efs-csi-values.yaml
	@kubectl create configmap efs-csi-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/efs-csi-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# FSx CSI values
	@echo 'controller:' > $(GENERATED_DIR)/fsx-csi-values.yaml
	@echo '  serviceAccount:' >> $(GENERATED_DIR)/fsx-csi-values.yaml
	@echo '    annotations:' >> $(GENERATED_DIR)/fsx-csi-values.yaml
	@echo '      eks.amazonaws.com/role-arn: $(FSX_ROLE_ARN)' >> $(GENERATED_DIR)/fsx-csi-values.yaml
	@kubectl create configmap fsx-csi-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/fsx-csi-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -
	
	@# Secrets Store CSI values
	@echo 'linux:' > $(GENERATED_DIR)/secrets-store-csi-values.yaml
	@echo '  serviceAccount:' >> $(GENERATED_DIR)/secrets-store-csi-values.yaml
	@echo '    annotations:' >> $(GENERATED_DIR)/secrets-store-csi-values.yaml
	@echo '      eks.amazonaws.com/role-arn: $(SS_ROLE_ARN)' >> $(GENERATED_DIR)/secrets-store-csi-values.yaml
	@kubectl create configmap secrets-store-csi-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/secrets-store-csi-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -

	@# AWS Load Balancer Controller values
	@echo 'clusterName: $(CLUSTER_NAME)' > $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@echo 'region: $(REGION)' >> $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@echo 'vpcId: $(VPC_ID)' >> $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@echo 'serviceAccount:' >> $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@echo '  annotations:' >> $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@echo '    eks.amazonaws.com/role-arn: $(ALB_ROLE_ARN)' >> $(GENERATED_DIR)/aws-lb-controller-values.yaml
	@kubectl create configmap aws-lb-controller-values \
		--namespace flux-system \
		--from-file=values.yaml=$(GENERATED_DIR)/aws-lb-controller-values.yaml \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "==> cluster-config ConfigMaps created/updated"

# Update cluster-config (run after IAM stack update)
cluster-config-update: _create-cluster-config
	@echo "==> Restarting Flux to pick up new config..."
	-kubectl rollout restart deployment -n flux-system

# ==============================================================================
# IAM Stack Management
# ==============================================================================
.PHONY: _deploy-iam

_deploy-iam: _check-params
	@echo "==> Deploying IAM stack: $(IAM_STACK_NAME)"
	@# Deploy IAM roles required for cluster creation (Karpenter, Node roles)
	@# OIDC-dependent roles will be incomplete until iam-update is run post-cluster
	aws cloudformation deploy \
		--stack-name $(IAM_STACK_NAME) \
		--template-file $(IAM_TEMPLATE) \
		--parameter-overrides \
			Environment=$(ENV) \
			ClusterName=$(CLUSTER_NAME) \
		--capabilities CAPABILITY_NAMED_IAM \
		--tags skyhook.io/environment=$(ENV) skyhook.io/cluster=$(CLUSTER_NAME) \
		--region $(REGION) \
		--no-fail-on-empty-changeset
	@echo "==> Waiting for IAM stack to complete..."
	@aws cloudformation wait stack-create-complete --stack-name $(IAM_STACK_NAME) --region $(REGION) 2>/dev/null || \
		aws cloudformation wait stack-update-complete --stack-name $(IAM_STACK_NAME) --region $(REGION) 2>/dev/null || true
	@echo "==> Verifying Karpenter role exists..."
	@aws iam get-role --role-name $(CLUSTER_NAME)-karpenter --region $(REGION) > /dev/null || \
		(echo "ERROR: Karpenter role $(CLUSTER_NAME)-karpenter not found. Check CloudFormation stack." && exit 1)
	@echo "==> IAM stack deployed successfully"

# Update IAM stack with OIDC provider after cluster creation
iam-update: _check-params
	$(eval OIDC_ISSUER := $(shell aws eks describe-cluster --name $(CLUSTER_NAME) --query 'cluster.identity.oidc.issuer' --output text --region $(REGION)))
	$(eval OIDC_ID := $(shell echo $(OIDC_ISSUER) | sed 's|https://oidc.eks.$(REGION).amazonaws.com/id/||'))
	@echo "==> Updating IAM stack with OIDC: $(OIDC_ID)"
	aws cloudformation update-stack \
		--stack-name $(IAM_STACK_NAME) \
		--template-body file://$(IAM_TEMPLATE) \
		--parameters \
			ParameterKey=Environment,ParameterValue=$(ENV) \
			ParameterKey=ClusterName,ParameterValue=$(CLUSTER_NAME) \
			ParameterKey=OidcId,ParameterValue=$(OIDC_ID) \
		--capabilities CAPABILITY_NAMED_IAM \
		--region $(REGION)
	aws cloudformation wait stack-update-complete --stack-name $(IAM_STACK_NAME) --region $(REGION)

# ==============================================================================
# Flux Bootstrap
# ==============================================================================
.PHONY: flux-bootstrap flux-status

flux-bootstrap: _check-params
	$(eval KUBE_CONTEXT := $(shell kubectl config get-contexts -o name | grep $(CLUSTER_NAME) | head -n 1))
	@if [ -z "$(KUBE_CONTEXT)" ]; then echo "Error: Context for $(CLUSTER_NAME) not found"; exit 1; fi
	@echo "==> Installing Flux CD components and CRDs on $(CLUSTER_NAME) (Context: $(KUBE_CONTEXT))"
	flux install \
		--context $(KUBE_CONTEXT) \
		--namespace flux-system \
		--network-policy=false \
		--components-extra=image-reflector-controller,image-automation-controller
	@echo "==> Waiting for Flux to be ready..."
	kubectl wait --for=condition=Ready kustomization/flux-system -n flux-system --timeout=300s --context $(KUBE_CONTEXT) 2>/dev/null || true
	@echo "==> Applying layered Flux Kustomizations for platform components on $(CLUSTER_NAME)"
	kubectl apply -k ../clusters/base --context $(KUBE_CONTEXT)
	@echo "==> Waiting for platform controllers to reconcile..."
	kubectl wait --for=condition=Ready kustomization/controllers -n flux-system --timeout=300s --context $(KUBE_CONTEXT)
	@echo "==> Flux bootstrap and platform components applied!"

flux-status: _check-params
	$(eval KUBE_CONTEXT := $(shell kubectl config get-contexts -o name | grep $(CLUSTER_NAME) | head -n 1))
	@echo "==> Flux Status on $(CLUSTER_NAME) (Context: $(KUBE_CONTEXT))"
	flux get all --context $(KUBE_CONTEXT)

# ==============================================================================
# Promotion (update DNS/config to point users to this cluster)
# ==============================================================================
.PHONY: cluster-promote

cluster-promote: _check-params
	@echo "==> Promoting cluster $(CLUSTER_NAME) as active for $(ENV)"
	@echo "This will update SSM parameter /skyhook/$(ENV)/active-cluster"
	@read -p "Confirm promotion? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	aws ssm put-parameter \
		--name /skyhook/$(ENV)/active-cluster \
		--value $(CLUSTER_NAME) \
		--type String \
		--overwrite \
		--region $(REGION)
	@echo "==> $(CLUSTER_NAME) is now the active cluster for $(ENV)"

# ==============================================================================
# Help
# ==============================================================================
.PHONY: help
help:
	@echo "Skyhook Cluster Releases"
	@echo ""
	@echo "Usage: make <target> ENV=<environment> CLUSTER=<release>"
	@echo ""
	@echo "Lifecycle:"
	@echo "  cluster-up       Create new cluster release on foundation"
	@echo "  cluster-down     Delete cluster release"
	@echo "  cluster-status   Show cluster status"
	@echo "  cluster-list     List all clusters in environment"
	@echo "  cluster-config   Generate eksctl config only (no create)"
	@echo ""
	@echo "Flux:"
	@echo "  flux-bootstrap   Apply Flux bootstrap to cluster"
	@echo "  flux-status      Show Flux reconciliation status"
	@echo ""
	@echo "Promotion:"
	@echo "  cluster-promote  Set this cluster as active for environment"
	@echo ""
	@echo "IAM:"
	@echo "  iam-update       Update IAM stack with cluster OIDC provider"
	@echo ""
	@echo "Example:"
	@echo "  make cluster-up ENV=accel-usw2 CLUSTER=v42"
	@echo "  make cluster-status ENV=accel-usw2 CLUSTER=v42"
	@echo "  make cluster-promote ENV=accel-usw2 CLUSTER=v42"

