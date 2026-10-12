# Schema-qualified tables in a small application

This example gives reviewers a runnable document/statement application with
synthetic data. It uses ordinary Django models, ORM queries, and migrations.
There is no RulorAI, web server, cloud service, or production-data dependency.

Two independent paths separate the existing upstream proposal from this fork's
additional behavior:

| Path | Ownership | Evidence |
| --- | --- | --- |
| `unmanaged_records`, `unmanaged_settings` | Existing tables provisioned by SQL; `managed = False` | CRUD, a cross-schema foreign key and joined read, two tables named `record` in different schemas, migration serialization, and preservation of external tables on migration reversal |
| `managed_records`, default `settings` | Tables owned by Django migrations | CRUD, cross-schema foreign key and joined read, field addition/reversal, complete migration reversal/reapplication, and flush |

The unmanaged path targets [Django PR #21757](https://github.com/django/django/pull/21757),
by Bader Eddine Benhirt, for [ticket #6148](https://code.djangoproject.com/ticket/6148).
The managed path exercises downstream additions. This example does not propose
expanding the precursor PR's scope. Coordinate managed follow-ups with its author
and Django maintainers once the foundational public API is accepted.

## Run from the fork checkout

Requirements: Python 3.12+ and Docker for a disposable PostgreSQL instance.
The fork's existing CI matrix exercises PostgreSQL 16 and 17 on Python 3.12.
The commands below use PostgreSQL 18, the version used for local verification.

From the repository root:

```sh
python -m venv .venv
.venv/bin/python -m pip install -e . 'psycopg[binary]'
docker run --rm -d --name schema-support-example \
  -e POSTGRES_DB=schema_example -e POSTGRES_PASSWORD=example-only \
  -p 127.0.0.1:55432:5432 postgres:18
export PGDATABASE=schema_example PGUSER=postgres PGPASSWORD=example-only
export PGHOST=127.0.0.1 PGPORT=55432
until docker exec schema-support-example pg_isready -U postgres; do sleep 1; done
```

Use a dedicated database: the examples create fixture objects and the tests need
permission to create a test database. The container's role provides that permission.
Only this disposable setup uses the example password.

### Unmanaged tables: precursor PR

```sh
.venv/bin/python examples/schema_support/manage.py test unmanaged_records \
  --settings=unmanaged_settings --noinput -v2
.venv/bin/python examples/schema_support/manage.py demo_unmanaged \
  --settings=unmanaged_settings
```

Expected: five tests pass and the command prints
`Unmanaged CRUD and cross-schema join passed.`

The SQL fixture creates `example_legacy_docs.record` and
`example_legacy_rows.record`. Django accesses these externally owned tables;
the unmanaged migration records model state without creating or deleting tables.
Reversing that migration leaves the external rows readable. The demonstration
removes only its own synthetic rows and leaves the fixture tables in place.

To verify against the actual precursor PR rather than this fork:

```sh
git fetch https://github.com/django/django.git pull/21757/head
git worktree add --detach /tmp/django-schema-precursor FETCH_HEAD
PYTHONPATH=/tmp/django-schema-precursor .venv/bin/python -c \
  'import django; print(django.__file__)'
PYTHONPATH=/tmp/django-schema-precursor .venv/bin/python \
  examples/schema_support/manage.py test unmanaged_records \
  --settings=unmanaged_settings --noinput -v2
```

The printed Django path must be under `/tmp/django-schema-precursor`.
Use a fresh worktree path if that path already exists. This selects the precursor's
Django implementation while running this example's unmanaged app; no managed app
is installed under `unmanaged_settings`.

### Managed tables: downstream follow-up

```sh
.venv/bin/python examples/schema_support/manage.py test \
  managed_records unmanaged_records --noinput -v2
.venv/bin/python examples/schema_support/manage.py makemigrations --check --dry-run
.venv/bin/python examples/schema_support/manage.py migrate --noinput
.venv/bin/python examples/schema_support/manage.py demo_managed
```

Expected: eight tests pass, no migration changes are detected, and the command
prints `Managed CRUD, migrated field, and cross-schema join passed.`

`Document` lives in `example_documents`; `Statement` lives in `example_statements`.
The initial migration creates those schemas before the tables. The second adds
the `note` field. Tests reverse the field migration, preserve an existing row
while adding the field again, reverse all model migrations, and recreate the
tables with a working relation. Empty schemas remain on reversal; ordinary
migrations never drop schemas with `CASCADE`. Another test flushes records and
then creates new related rows.

Both demos are repeatable. Test setup, migration reversal, and test teardown run
inside Django's separate `test_schema_example` database. To remove the disposable
database and all example objects when finished:

```sh
docker stop schema-support-example
git worktree remove /tmp/django-schema-precursor  # If created for precursor testing.
```

## Application case study: RulorAI

[RulorAI](https://github.com/HundredBillion/rulorai) turns statement PDFs into a
reviewable transaction table. It uses fixed, module-owned PostgreSQL schemas for
documents, extraction, statements, review, jobs, and other application areas.
Managed migrations and relations across those schemas are why the application
needs the downstream additions beyond unmanaged table references.

The dependency update in [RulorAI PR #17](https://github.com/HundredBillion/rulorai/pull/17)
pins fork commit `4d631ce511a43d01051e8b25fbc2d98fc984b38c`. Its clean local
candidate `4c8981f37d90a6f55c193e32c5f938eb61dbba51` passed 380 Django tests,
including PostgreSQL and Chromium workflows, 48 JavaScript tests, import checks,
migration drift checks, Django system checks, and the application's bug-register
check. These are synthetic integration results, not a deployment attestation.

## Evidence and limits

Local validation on October 12, 2026 uses Python 3.14.7 and PostgreSQL 18.
The unmanaged example was also exercised using precursor PR #21757 at
`78ee552ecc17b27bd002f1570e9a2eaf67e8ddf8`; this tests the precursor directly,
not merely its attributed patch inside this fork. Test counts above describe
this example, not Django's full suite. CI results must be checked separately.

The example demonstrates static PostgreSQL schemas. It does not establish
support for dynamic tenant schemas, other database backends, full schema-aware
`inspectdb`, role/grant management, or production deployment behavior. It is
supplementary evidence; framework regression tests and maintainer review remain
necessary. This example and documentation were prepared with OpenAI Codex
assistance and verified through the commands described above.
