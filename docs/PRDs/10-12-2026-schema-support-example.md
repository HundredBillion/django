# Schema support application example

Give Django reviewers a small reproducible application using synthetic data,
without requiring RulorAI, cloud services, or changes to Django internals.

## Acceptance criteria

1. An unmanaged-only settings module demonstrates SQL-provisioned tables,
   CRUD, a cross-schema foreign key and join, duplicate table names in separate
   schemas, and serialization of schema-qualified table identities.
2. The unmanaged example can be exercised independently of managed support.
3. Managed models demonstrate two schemas, cross-schema relations, and a field
   migration. Tests apply, reverse, and reapply the migrations and exercise flush.
4. A command demonstrates each application using synthetic data. Setup commands
   install the current checkout and use a disposable PostgreSQL database.
5. CI runs both examples on PostgreSQL 16 and 17 alongside existing regressions.
6. Reviewer documentation separates precursor PR #21757 from downstream managed
   behavior, preserves attribution, and describes measured evidence and limits.

## Decisions

Use two small Django apps in one example directory, not a copy of RulorAI.
Unmanaged tables are provisioned explicitly with SQL outside migrations; managed
migrations create their schemas and leave the empty schemas on reversal. Never
drop a schema with CASCADE during ordinary reversal. Use native Django test
databases. No web UI, tenant switching, production credentials, or framework
behavior changes. Tests on the fork alone do not prove compatibility with the
precursor PR; verify that separately where feasible.

Design review resolved table ownership, test database isolation, schema reversal,
and attribution within the user's approved scope. No essential requirements remain
unresolved. Routine review gates are approved by the user's workflow preference.
