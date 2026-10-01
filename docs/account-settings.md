# Account settings and Telegram readiness

`PUT /api/auth/account/me/settings` replaces the complete preferences object in
`UserModel.settings`. When `telegramBots` differs from the stored object, including removal,
the account use case checks the owning bot service before persisting any preferences.
Only a `ready` response permits that write. Disabled, connecting, failed, malformed,
unreachable, or timed-out status responses return a sanitized, uncached `503` and leave
all stored settings unchanged.

When `telegramBots` is unchanged, language, theme, and time zone can be saved without a
readiness request. Clients must retain the stored bot preferences when changing other
preferences because this remains a complete-object replacement.

Infrastructure must provide `TELEGRAM_PERSONAL_WORKSPACE_STATUS_URL` for the active
Personal Workspace backend's `GET /api/internal/telegram/status`. Auth API sends the shared
`TELEGRAM_SERVICE_SECRET` in `X-Telegram-Service-Secret`. The request has a three-second
total timeout, does not follow redirects, and accepts at most 1 KiB of JSON. The endpoint
and credential remain internal; Auth API stores only user preferences.
