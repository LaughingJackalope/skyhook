#!/bin/bash

# Tail CloudWatch logs for Karpenter conformance tests
# Usage: ./tail-karpenter-logs.sh [test-name]

set -euo pipefail

CLUSTER_NAME="skyhook-accel-usw2-v42"
REGION="us-west-2"
TEST_NAMESPACE="karpenter-conformance-testing"

# Log groups to monitor
LOG_GROUPS=(
    "/aws/eks/${CLUSTER_NAME}/cluster"
    "/aws/containerinsights/${CLUSTER_NAME}/application"
    "/aws/containerinsights/${CLUSTER_NAME}/host"
    "/aws/containerinsights/${CLUSTER_NAME}/dataplane"
)

# Function to tail logs with filter
tail_logs() {
    local log_group=$1
    local filter_pattern=${2:-""}
    local start_time=${3:-"5m"}
    
    echo "=== Tailing ${log_group} ==="
    
    if [[ -n "$filter_pattern" ]]; then
        aws logs tail "$log_group" \
            --region "$REGION" \
            --since "$start_time" \
            --filter-pattern "$filter_pattern" \
            --follow
    else
        aws logs tail "$log_group" \
            --region "$REGION" \
            --since "$start_time" \
            --follow
    fi
}

# Function to tail Karpenter specific logs
tail_karpenter_logs() {
    local test_filter=${1:-""}
    
    echo "Tailing Karpenter logs for cluster: $CLUSTER_NAME"
    echo "Test filter: ${test_filter:-"(all)"}"
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Karpenter controller logs
    tail_logs "/aws/containerinsights/${CLUSTER_NAME}/application" \
        "{ $.kubernetes.namespace_name = \"karpenter\" || $.kubernetes.pod_name = \"karpenter-*\" ${test_filter:+|| \$.message = \"*${test_filter}*\"} }" \
        "10m" &
    
    # Node provisioning events
    tail_logs "/aws/eks/${CLUSTER_NAME}/cluster" \
        "{ \$.responseElements.nodegroup.nodegroupName = \"*\" || \$.eventName = \"CreateNodegroup\" || \$.eventName = \"DeleteNodegroup\" }" \
        "10m" &
    
    # Wait for background processes
    wait
}

# Function to tail test-specific logs
tail_test_logs() {
    local test_name=$1
    
    echo "Tailing logs for test: $test_name"
    
    # Application logs for the test namespace
    tail_logs "/aws/containerinsights/${CLUSTER_NAME}/application" \
        "{ \$.kubernetes.namespace_name = \"${TEST_NAMESPACE}\" && \$.kubernetes.pod_name = \"*${test_name}*\" }" \
        "5m" &
    
    # Karpenter logs related to the test
    tail_logs "/aws/containerinsights/${CLUSTER_NAME}/application" \
        "{ \$.kubernetes.namespace_name = \"karpenter\" && \$.message = \"*${test_name}*\" }" \
        "5m" &
    
    wait
}

# Main execution
case "${1:-all}" in
    "karpenter")
        tail_karpenter_logs "${2:-}"
        ;;
    "test-"*)
        tail_test_logs "$1"
        ;;
    "all")
        echo "Available options:"
        echo "  karpenter [filter]  - Tail Karpenter controller logs"
        echo "  test-<name>        - Tail logs for specific test"
        echo "  all                - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 karpenter"
        echo "  $0 karpenter gpu"
        echo "  $0 test-gpu-standard"
        ;;
    *)
        echo "Unknown option: $1"
        echo "Run '$0 all' for help"
        exit 1
        ;;
esac