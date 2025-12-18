# ==============================================================================
# Makefile for Skyhook Foundation Layer
# ==============================================================================
#
# The foundation layer is long-lived infrastructure that cluster releases
# are built upon. It includes VPC, FSx, placement groups, and VPC endpoints.
#
# Usage:
#   make foundation-up ENV=accel-usw2
#   make foundation-status ENV=accel-usw2
#   make foundation-down ENV=accel-usw2

# Required parameter
ENV ?=

# Derived values
STACK_NAME = skyhook-$(ENV)-foundation
TEMPLATE_DIR = templates
PARAMS_FILE = params/$(ENV).json
REGION ?= us-west-2

# S3 bucket for nested templates (created if not exists)
TEMPLATE_BUCKET ?= skyhook-$(ENV)-cfn-templates

# ==============================================================================
# Validation
# ==============================================================================
.PHONY: _check-env
_check-env:
ifndef ENV
	$(error ENV is required. Usage: make <target> ENV=<environment>)
endif
	@if [ ! -f "$(PARAMS_FILE)" ]; then \
		echo "ERROR: Parameters file not found: $(PARAMS_FILE)"; \
		echo "Create it from params/example.json or use an existing environment."; \
		exit 1; \
	fi

# ==============================================================================
# Foundation Lifecycle
# ==============================================================================
.PHONY: foundation-up foundation-down foundation-status foundation-update

# Package templates to S3 and deploy the foundation stack
# Uses 'deploy' which handles both create and update
foundation-up: _check-env _package-templates
	@echo "==> Deploying foundation stack: $(STACK_NAME)"
	@# Convert JSON params to key=value format and add TemplateBaseUrl
	$(eval PARAMS := $(shell cat $(PARAMS_FILE) | jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' | tr '\n' ' '))
	aws cloudformation deploy \
		--stack-name $(STACK_NAME) \
		--template-file $(TEMPLATE_DIR)/main.yaml \
		--s3-bucket $(TEMPLATE_BUCKET) \
		--s3-prefix templates \
		--parameter-overrides $(PARAMS) TemplateBaseUrl=https://$(TEMPLATE_BUCKET).s3.$(REGION).amazonaws.com \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--tags skyhook.io/environment=$(ENV) skyhook.io/layer=foundation \
		--region $(REGION) \
		--no-fail-on-empty-changeset
	@echo "==> Foundation stack deployed successfully!"
	@$(MAKE) foundation-status ENV=$(ENV)

# Update existing foundation stack (alias for foundation-up since deploy handles both)
foundation-update: foundation-up

# Show foundation stack status and outputs
foundation-status: _check-env
	@echo "==> Foundation Stack Status: $(STACK_NAME)"
	@echo ""
	@aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query 'Stacks[0].StackStatus' \
		--output text \
		--region $(REGION) 2>/dev/null || echo "Stack not found"
	@echo ""
	@echo "==> Foundation Outputs:"
	@aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
		--output table \
		--region $(REGION) 2>/dev/null || echo "No outputs (stack may not exist)"

# Delete foundation stack (DANGEROUS - destroys FSx data!)
foundation-down: _check-env
	@echo "!!! WARNING: This will delete the foundation including FSx data !!!"
	@echo "Stack: $(STACK_NAME)"
	@read -p "Type 'destroy $(ENV)' to confirm: " confirm && \
		[ "$$confirm" = "destroy $(ENV)" ] || (echo "Aborted." && exit 1)
	@echo "==> Deleting foundation stack..."
	aws cloudformation delete-stack \
		--stack-name $(STACK_NAME) \
		--region $(REGION)
	@echo "==> Waiting for stack deletion..."
	aws cloudformation wait stack-delete-complete \
		--stack-name $(STACK_NAME) \
		--region $(REGION)
	@echo "==> Foundation stack deleted."

# ==============================================================================
# Template Management
# ==============================================================================
.PHONY: _package-templates _ensure-bucket

# Ensure S3 bucket exists for templates
_ensure-bucket:
	@aws s3api head-bucket --bucket $(TEMPLATE_BUCKET) --region $(REGION) 2>/dev/null || \
		(echo "==> Creating template bucket: $(TEMPLATE_BUCKET)" && \
		aws s3api create-bucket \
			--bucket $(TEMPLATE_BUCKET) \
			--region $(REGION) \
			--create-bucket-configuration LocationConstraint=$(REGION) && \
		aws s3api put-bucket-versioning \
			--bucket $(TEMPLATE_BUCKET) \
			--versioning-configuration Status=Enabled)

# Upload templates to S3
_package-templates: _ensure-bucket
	@echo "==> Uploading templates to s3://$(TEMPLATE_BUCKET)/"
	aws s3 sync $(TEMPLATE_DIR)/ s3://$(TEMPLATE_BUCKET)/ \
		--exclude "*" --include "*.yaml" \
		--region $(REGION)

# ==============================================================================
# Validation & Linting
# ==============================================================================
.PHONY: lint validate

# Lint CloudFormation templates
lint:
	@echo "==> Linting CloudFormation templates..."
	cfn-lint $(TEMPLATE_DIR)/*.yaml

# Validate templates against AWS
validate: _check-env _package-templates
	@echo "==> Validating templates..."
	@for template in $(TEMPLATE_DIR)/*.yaml; do \
		echo "Validating $$template..."; \
		aws cloudformation validate-template \
			--template-url https://$(TEMPLATE_BUCKET).s3.$(REGION).amazonaws.com/$$(basename $$template) \
			--region $(REGION) > /dev/null; \
	done
	@echo "==> All templates valid!"

# ==============================================================================
# SSM Parameter Helpers
# ==============================================================================
.PHONY: ssm-list ssm-get-metadata

# List all SSM parameters for this environment
ssm-list: _check-env
	@echo "==> SSM Parameters for /skyhook/$(ENV)/"
	@aws ssm get-parameters-by-path \
		--path /skyhook/$(ENV)/ \
		--recursive \
		--query 'Parameters[*].[Name,Value]' \
		--output table \
		--region $(REGION)

# Get foundation metadata JSON
ssm-get-metadata: _check-env
	@aws ssm get-parameter \
		--name /skyhook/$(ENV)/foundation-metadata \
		--query 'Parameter.Value' \
		--output text \
		--region $(REGION) | jq .

# ==============================================================================
# Help
# ==============================================================================
.PHONY: help
help:
	@echo "Skyhook Foundation Layer"
	@echo ""
	@echo "Usage: make <target> ENV=<environment>"
	@echo ""
	@echo "Lifecycle:"
	@echo "  foundation-up      Create new foundation (VPC, FSx, placement groups)"
	@echo "  foundation-update  Update existing foundation"
	@echo "  foundation-status  Show stack status and outputs"
	@echo "  foundation-down    Delete foundation (DESTROYS DATA!)"
	@echo ""
	@echo "Validation:"
	@echo "  lint               Run cfn-lint on templates"
	@echo "  validate           Validate templates against AWS API"
	@echo ""
	@echo "SSM:"
	@echo "  ssm-list           List all SSM parameters for environment"
	@echo "  ssm-get-metadata   Get foundation metadata JSON"
	@echo ""
	@echo "Environments:"
	@ls -1 params/*.json 2>/dev/null | sed 's/params\///;s/\.json//' | sed 's/^/  /'
	@echo ""
	@echo "Example:"
	@echo "  make foundation-up ENV=accel-usw2"

