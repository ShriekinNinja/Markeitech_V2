## Scope

- What stage or slice does this PR implement?
- What is intentionally out of scope?

## Contracts and behavior

- [ ] Actor, event, persistence, provider, or configuration contracts changed: describe them.
- [ ] No runtime/business behavior changed outside the stated scope.

## Verification

- [ ] Ruff passed.
- [ ] Offline V2 tests passed.
- [ ] PostgreSQL integration tests passed, when applicable.
- [ ] Live acceptance status is stated below.

Live acceptance status: `not run` / `run and passed` / `run with findings` / `not applicable`

## Operations and data

- [ ] PostgreSQL migration impact is described, or `none`.
- [ ] Configuration or environment-variable changes are documented.
- [ ] Documentation was updated, or `none` is explained.

## Integrity checklist

- [ ] No secrets, webhook URLs, passwords, tokens, or local `.env` files were committed.
- [ ] No raw market data was committed.
- [ ] No live IB/TWS, Discord, or execution path was invoked by CI.
