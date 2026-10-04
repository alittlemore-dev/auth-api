# Personal API tokens

The account page `/account/api-access` manages named credentials for the public APIs:

- `https://alittlemore.dev/api/auth`
- `https://alittlemore.dev/api/personal-workspace`
- `https://alittlemore.dev/api/competency`

The combined operation reference is `https://alittlemore.dev/api/docs`. Protected OpenAPI
operations state their required PAT permissions. Internal service APIs and Telegram webhooks
keep their own authentication.

## Management contract

All operations under `/api/auth/account/me/api-tokens` require the owner's ordinary browser
session. PATs cannot manage PATs. Browser mutations use the existing CSRF guard.

| Method and suffix | Result |
| --- | --- |
| `GET /permissions` | Concrete permission catalog filtered by the current role |
| `GET` | Metadata only; no secrets |
| `POST` | Create using `name`, `permissions`, `expiresAt` and current `password` |
| `POST /{id}/reveal` | Return the same active secret after checking the current `password` |
| `POST /{id}/revoke` | Revoke only this token |

Creation returns `{token: metadata, secret}`; reveal returns `{secret}`. Secret responses use
`Cache-Control: no-store`. Each creation, reveal and copy confirms the password separately.
Incorrect password confirmation and an inactive token are action failures; an invalid browser
credential remains an authentication failure so the frontend can refresh its session.

Scopes and expiry cannot be edited. The UI defaults to one hour and supports one day, 7, 30,
90 and 365 days or a custom future date within 365 days. “All available permissions” stores the
current catalog snapshot: new permissions are never added to an existing credential.

## Storage and lifecycle

The separate PAT table stores the owner, name, immutable scope list, creation/expiry/last-use
and revocation timestamps. Authentication compares a SHA-256 hash of a random opaque secret.
`EncryptedString` stores an encrypted recoverable copy; revealing decrypts the same value,
rather than issuing a replacement token. The encryption key is a required server secret.

Logout revokes only the browser session. Password changes and account deactivation revoke all
PATs; deleting the account cascades to its PAT records. Verification reloads the active account
and intersects selected permissions with its current role. Role reduction and ownership checks
therefore apply even to an already issued token.

PAT verification v2 explicitly forbids caching. The old verification contract rejects PATs.
A completed revocation blocks the next verification; an already authenticated request may
finish. PAT session administration has no current browser session: `isCurrent` is false and
revoking other sessions means all browser sessions of the permitted target account.

Password checks use the existing Argon2 hasher and rate limit. Request bodies, authorization
headers, cookies, exception locals and validation input values are excluded from credential
logging and Sentry events. The frontend retains a revealed secret only in page memory and
clears it on hide or navigation; copying performs another password-confirmed reveal.

## Transition

Auth verification v2 is installed first, then SDK 0.3.0 and consumer services, then token issuance
UI. Publish the SDK separately before updating production registry dependencies/lockfiles.
Local checks and `infra make dev` use the actual built wheel without a package release.
Agent Access is retired by competency migration 0021; historical migrations remain intact.
Only agent records and types are removed. Downgrade restores empty agent tables, not deleted data.
