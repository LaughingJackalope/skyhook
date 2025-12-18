# Architecture Decision Records

Architecture Decision Records (ADRs) capture important architectural decisions made during Skyhook development, including the context, decision, and consequences.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-fsx-over-s3.md) | FSx for Lustre over Mountpoint for S3 | Accepted | 2024 |
| [002](002-kyverno-policies.md) | Kyverno for Policy Automation | Accepted | 2024 |
| [003](003-soci-image-loading.md) | SOCI for Container Image Loading | Accepted | 2024 |

## ADR Template

When creating a new ADR, use this template:

```markdown
# ADR-NNN: Title

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

What is the issue that we're seeing that motivates this decision?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or harder as a result of this decision?

### Positive

- Benefit 1
- Benefit 2

### Negative

- Drawback 1
- Drawback 2

### Neutral

- Tradeoff 1

## Alternatives Considered

What other options were evaluated?

### Alternative A

Description and why it was not chosen.

### Alternative B

Description and why it was not chosen.
```

## Principles

Our architectural decisions are guided by:

1. **Researcher Experience (RX) First** — Minimize friction, maximize productivity
2. **Performance over Simplicity** — Choose the high-performance path even when operationally complex
3. **Automation over Documentation** — Automate configuration rather than document manual steps
4. **Fail Fast** — Surface errors quickly rather than degrading silently

