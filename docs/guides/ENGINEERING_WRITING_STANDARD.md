# Engineering Writing Standard (Human Style)

This file defines how future code and docs should look in this repository.
Use this as a hard rule for all expansions.

## 1) Code structure rules

- One file should have one clear responsibility.
- Keep function names short but concrete.
- Avoid hidden magic constants; use named constants or config fields.
- Keep backward compatibility when changing public APIs.

## 2) Comment style rules

- Write comments for intent, not for syntax.
- Good comment:
  - Why this branch exists.
  - What threat model this check mitigates.
- Bad comment:
  - Restating obvious Python syntax.
- Prefer short English technical comments in core security logic.

## 3) Security logic rules

- Any public helper metadata must have integrity protection.
- Any secret or key equality check must be constant-time.
- Separate these stages explicitly:
  - Error correction
  - Integrity verification
  - Privacy amplification
  - Authentication decision

## 4) Testing rules

- Every security feature needs at least one positive and one adversarial test.
- Keep deterministic seeds for regression tests.
- Stress tests must include non-IID noise (clustered/burst cases).

## 5) Language and readability

- Avoid over-marketing language in code comments.
- Avoid template-like repeated phrasing.
- Prefer precise terms over broad claims.
- If uncertainty exists, state assumptions directly.

## 6) Commit message style

Use practical, reviewable commit titles:

- `security: add HMAC verification for helper data`
- `auth: add SHA-256 privacy amplification gate`
- `ecc: add optional interleaving against burst errors`

Avoid vague messages like:

- `update code`
- `fix bug`
- `improve system`

## 7) Doc update requirement

When changing security behavior, update at least one report under `docs/reports` with:

- threat model
- what changed
- what remains unproven
- how to reproduce results
