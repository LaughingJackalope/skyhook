# ==============================================================================
# EC2NodeClasses - AWS-specific node configuration for Karpenter v1.x
# ==============================================================================
# Three classes optimized for different workload types:
#   - default: General-purpose workloads in system subnets
#   - gpu: GPU workloads with NVIDIA drivers in HPC subnets
#   - hpc: High-performance distributed workloads with EFA and FSx
# ==============================================================================
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: default
spec:
  amiFamily: Bottlerocket
  amiSelectorTerms:
    - alias: bottlerocket@latest
  subnetSelectorTerms:
    - tags:
        skyhook.io/subnet-role: system
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  instanceProfile: ${CLUSTER_NAME}-karpenter-node
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 4Gi
        volumeType: gp3
        encrypted: true
        deleteOnTermination: true
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 100Gi
        volumeType: gp3
        iops: 3000
        throughput: 125
        encrypted: true
        deleteOnTermination: true
  metadataOptions:
    httpEndpoint: enabled
    httpProtocolIPv6: disabled
    httpPutResponseHopLimit: 2
    httpTokens: required
  tags:
    skyhook.io/nodeclass: default
    skyhook.io/managed-by: karpenter
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: gpu
spec:
  amiFamily: Bottlerocket
  amiSelectorTerms:
    - alias: bottlerocket@latest
  subnetSelectorTerms:
    - tags:
        skyhook.io/subnet-role: hpc
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  instanceProfile: ${CLUSTER_NAME}-karpenter-node
  instanceStorePolicy: RAID0
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 4Gi
        volumeType: gp3
        encrypted: true
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 20Gi
        volumeType: gp3
        encrypted: true
  userData: |
    [settings.kubernetes]
    "allowed-unsafe-sysctls" = ["net.ipv4.tcp_*", "net.core.somaxconn"]
    
    [settings.container-runtime]
    snapshotter = "soci"
    
    [settings.container-runtime-plugins.soci-snapshotter]
    pull-mode = "parallel-pull-unpack"
  tags:
    skyhook.io/nodeclass: gpu
    skyhook.io/managed-by: karpenter
---
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
metadata:
  name: hpc
spec:
  amiFamily: Bottlerocket
  amiSelectorTerms:
    - alias: bottlerocket@latest
  subnetSelectorTerms:
    - tags:
        skyhook.io/subnet-role: hpc
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: ${CLUSTER_NAME}
  instanceProfile: ${CLUSTER_NAME}-karpenter-node
  instanceStorePolicy: RAID0
  blockDeviceMappings:
    - deviceName: /dev/xvda
      ebs:
        volumeSize: 4Gi
        volumeType: gp3
        encrypted: true
        deleteOnTermination: true
    - deviceName: /dev/xvdb
      ebs:
        volumeSize: 50Gi
        volumeType: gp3
        encrypted: true
        deleteOnTermination: true
  userData: |
    [settings.kubernetes]
    "allowed-unsafe-sysctls" = ["net.ipv4.tcp_*", "net.core.somaxconn"]
    
    [settings.kernel.sysctl]
    "net.core.somaxconn" = "65535"
    "net.ipv4.tcp_max_syn_backlog" = "65535"
    "net.core.netdev_max_backlog" = "65535"
    
    [settings.container-runtime]
    snapshotter = "soci"
    
    [settings.container-runtime-plugins.soci-snapshotter]
    pull-mode = "parallel-pull-unpack"
  tags:
    skyhook.io/nodeclass: hpc
    skyhook.io/managed-by: karpenter
    skyhook.io/efa-enabled: "true"

