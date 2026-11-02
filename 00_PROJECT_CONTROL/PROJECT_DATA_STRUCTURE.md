# MARSEL ROAPP — Canonical Project Data Structure

The repository already contains code, audit engines, documentation, MCP, plugins, tests, and operational material. The goal is to make the logical architecture explicit without destructive bulk moves.

```text
MARSEL-ROAPP/
├── 00_PROJECT_CONTROL/       # governance, registry, state, decisions, roadmap
├── 01_ARCHITECTURE/          # system architecture and contracts
├── 02_ROAPP/                 # RO App API/client/integration contracts
├── 03_MARSEL_CORE/           # business domain: catalog, repairs, products, services
├── 04_COMMERCE/              # marketplace, social commerce, orders, customer flows
├── 05_FINANCE/               # costing, metal/stones, pricing, finance controls
├── 06_AI/                    # AI services, agents, prompts, evaluation contracts
├── 07_AUTOMATION/            # automation, jobs, orchestration, integrations
├── 08_SECURITY/              # security policies, threat model, secret handling
├── 09_QUALITY/               # tests, data quality, audit and evidence contracts
├── 10_OPERATIONS/            # deployment, backup/restore, runbooks, incident response
├── 11_ROADMAP/               # ordered delivery plan
├── app/                      # application/runtime code
├── ai_service/               # AI runtime implementation
├── config/                   # non-secret configuration
├── data/                     # safe fixtures/schemas; never live credentials
├── docs/                     # detailed technical/business documentation
├── plugins/                  # approved plugin bundles
├── python/                   # Python tooling/audits
├── javascript/               # JavaScript tooling
├── typescript/               # TypeScript tooling
├── scripts/                  # operational scripts
├── tests/                    # automated tests
├── .github/                  # GitHub governance and CI/CD
├── старые данные/            # historical archive; never used as current truth
└── root files                # only entrypoints/config/metadata that truly belong at root
```

## Root-file rule

New documentation must not be added to the repository root unless it is a canonical entrypoint (`README.md`, `SECURITY.md`, `AGENTS.md`, `VERSION`, or a narrowly justified technical entrypoint). New project-control documents belong under `00_PROJECT_CONTROL/` and domain documents under their domain directory.

## Data rule

Live ROAPP production data is not stored in Git. Git stores schemas, contracts, fixtures, audit metadata, and evidence manifests only. Credentials are never stored in Git.

## Migration rule

Existing files are not bulk-moved merely to make the tree look clean. A move is performed only when the target location is canonical, references are updated, tests pass, and the old location is proven obsolete.
