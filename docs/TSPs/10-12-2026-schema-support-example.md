# Schema Support Example Technical Spec

> **For agentic workers:** Use dmi-superpowers:executing-plans to implement inline.

**Goal:** Provide runnable unmanaged and managed schema support evidence.

**Architecture:** Two apps share connection configuration and a management entry
point. `unmanaged_settings` installs only unmanaged records. Tests use PostgreSQL
test databases and explicit unmanaged fixture ownership.

**Tech Stack:** Current Django checkout, Python 3.12+, PostgreSQL, psycopg.

## Global constraints

- Synthetic data only; no RulorAI runtime dependency.
- No Django framework behavior changes.
- Preserve precursor authorship and distinguish upstream from fork capabilities.
- Leave empty schemas on managed migration reversal; no cascading schema drop.

### Task 1: Unmanaged application

Files: `examples/schema_support/manage.py`, `settings.py`,
`unmanaged_settings.py`, `unmanaged_records/{models,fixtures,tests}.py`,
`unmanaged_records/management/commands/demo_unmanaged.py`, package initializers.

Consumes: `models.SchemaQualifiedTable(table, schema=...)` and standard ORM APIs.
Produces: an unmanaged-only runnable example and tests.

- [ ] Create connection settings and a test asserting CRUD and joined reads.
- [ ] Run the test before adding models and observe import failure.
- [ ] Add unmanaged models, SQL-owned fixtures, and demonstration command.
- [ ] Verify duplicate-name isolation, foreign-key integrity, cascade deletion,
      and serialization with Django integration tests.
- [ ] Run `python examples/schema_support/manage.py test unmanaged_records
      --settings=unmanaged_settings --noinput`; commit verified task.

### Task 2: Managed application

Files: `managed_records/models.py`, `managed_records/migrations/0001_initial.py`,
`0002_statement_note.py`, `managed_records/tests.py`,
`managed_records/management/commands/demo_managed.py`, package initializers.

Consumes: shared settings and public migration/ORM APIs.
Produces: two managed schema-qualified models and reversible migration evidence.

- [ ] Add the managed CRUD/join test and observe missing-model failure.
- [ ] Add Document and Statement models and migrations; rerun the test.
- [ ] Add migration roundtrip and flush tests, then run both example apps.
- [ ] Run `python examples/schema_support/manage.py makemigrations --check
      --dry-run`; commit verified task.

### Task 3: Reviewer documentation and CI

Files: example `README.md`, `.github/workflows/schema-support.yml`,
`docs/internals/schema-support-fork.txt`.

Consumes: verified application commands and exact test results.
Produces: reproducible instructions, upstream scope map, and CI example steps.

- [ ] Document disposable PostgreSQL setup, commands, expected output, limits,
      and the RulorAI case study with exact candidate verification evidence.
- [ ] Run unmanaged and managed examples in the existing PostgreSQL CI matrix.
- [ ] Verify the documented commands on PostgreSQL 18; verify unmanaged example
      against an isolated checkout of upstream PR #21757 where feasible.
- [ ] Run existing schema and migration regressions, formatting, documentation
      lint, and workflow syntax checks. Record precise results and limits.
- [ ] Commit, obtain an independent whole-branch review, and resolve findings.

## Review focus

Tests must demonstrate actual cross-schema SQL, not only expected query text.
Unmanaged fixtures must not become managed migrations. Migration reversal must
preserve schemas and historical rows when reversing just the field migration.
README instructions must work with the stated database permissions and checkout.
