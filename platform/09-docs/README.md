# Layer 09: Documentation

Skyhook platform documentation deployed as a static MkDocs site.

## Endpoint

- **Internal**: `http://docs.skyhook.internal`
- **Port-forward**: `kubectl port-forward -n docs svc/skyhook-docs 8080:80`

## Deployment Options

### Full Deploy (with ECR)

```bash
# Build, push to ECR, and deploy
make deploy-09
```

### Local Deploy (no ECR)

```bash
# Build locally and deploy (for development/testing)
make deploy-09-local

# Then port-forward to access
kubectl port-forward -n docs svc/skyhook-docs 8080:80
```

### Local Development

```bash
# From repo root, serve docs locally
pip install -r requirements-docs.txt
mkdocs serve

# Opens at http://localhost:8000
```

## Components

| Resource | Description |
|----------|-------------|
| `Deployment` | 2 replicas of nginx serving static docs |
| `Service` | ClusterIP on port 80 |
| `Ingress` | ALB ingress at `docs.skyhook.internal` |
| `PodDisruptionBudget` | Ensures at least 1 replica available |
| `ServiceAccount` | Dedicated SA for docs pods |

## Image

The docs image is built using `Dockerfile.docs` in the repo root:

1. **Build stage**: Python with MkDocs builds static HTML
2. **Runtime stage**: nginx:alpine serves the static files

Image is ~20MB and serves content on port 8080.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCS_IMAGE` | `skyhook-docs` | Image name |
| `DOCS_TAG` | `latest` | Image tag |
| `DOCS_REGISTRY` | `{account}.dkr.ecr.{region}.amazonaws.com` | ECR registry |

## Customization

To change the hostname, update the Ingress in `manifests/deployment.yaml`:

```yaml
spec:
  rules:
    - host: docs.your-domain.internal
```

For HTTPS, uncomment the ACM certificate annotations in the Ingress.


