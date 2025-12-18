#!/bin/bash

# Quick CloudWatch log queries for Karpenter conformance tests
# Usage: ./quick-logs.sh <command> [args]

CLUSTER_NAME="skyhook-accel-usw2-v42"
REGION="us-west-2"

case "$1" in
    "karpenter-errors")
        aws logs filter-log-events \
            --region "$REGION" \
            --log-group-name "/aws/containerinsights/${CLUSTER_NAME}/application" \
            --filter-pattern '{ $.kubernetes.namespace_name = "karpenter" && ($.level = "ERROR" || $.level = "WARN") }' \
            --start-time $(date -d '10 minutes ago' +%s)000
        ;;
    "node-events")
        aws logs filter-log-events \
            --region "$REGION" \
            --log-group-name "/aws/eks/${CLUSTER_NAME}/cluster" \
            --filter-pattern '{ $.eventName = "CreateNodegroup" || $.eventName = "DeleteNodegroup" || $.eventName = "UpdateNodegroupConfig" }' \
            --start-time $(date -d '30 minutes ago' +%s)000
        ;;
    "test-pods")
        aws logs filter-log-events \
            --region "$REGION" \
            --log-group-name "/aws/containerinsights/${CLUSTER_NAME}/application" \
            --filter-pattern '{ $.kubernetes.namespace_name = "karpenter-conformance-testing" }' \
            --start-time $(date -d '15 minutes ago' +%s)000
        ;;
    *)
        echo "Usage: $0 <command>"
        echo "Commands:"
        echo "  karpenter-errors  - Show Karpenter errors/warnings"
        echo "  node-events      - Show node provisioning events"
        echo "  test-pods        - Show test pod logs"
        ;;
esac