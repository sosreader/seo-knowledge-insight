---
name: "API changelog sync"
on:
  push:
    - repo: "sosreader/seo-knowledge-insight"
---

When a PR is merged that touches files under `api/`, review the changes and update the changelog page in `api/docs/`. 

Rules:
1. Only document user-facing API changes (new endpoints, schema changes, breaking changes, bug fixes)
2. Skip internal refactors, test-only changes, and CI/CD updates
3. Format each entry as: `- **[type]** Description` where type is Added/Changed/Fixed/Removed
4. Group entries under a date heading: `## YYYY-MM-DD`
5. If no user-facing changes exist, do nothing
