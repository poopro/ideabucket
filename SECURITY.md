# Security policy

Ideabucket stores private links, summaries, goals, and progress on the local machine.

## Reporting a vulnerability

Please do not open a public issue for vulnerabilities that could expose data, overwrite files,
or spend API credit. Contact the repository owner privately through GitHub first and include a
minimal reproduction. After a fix is available, a public advisory can document the impact.

## Local security model

- Telegram updates are accepted only from `TELEGRAM_OWNER_USER_ID`.
- Dashboard and extension API requests require `CAPTURE_TOKEN`.
- The server accepts only loopback hosts and does not grant CORS access to ordinary websites.
- Goal hashtags are validated before they are used in filenames.

