# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue
2. Email details to the repository maintainer via GitHub private security advisory
3. Include steps to reproduce, impact assessment, and suggested fix if available

We aim to acknowledge reports within 48 hours and provide a fix timeline within 7 days for critical issues.

## Scope

- Exchange API authentication and authorization
- Risk engine bypass vulnerabilities
- SQL injection in data connectors
- Remote code execution in ML pipeline custom expressions
- Docker container escape or privilege escalation

## Out of Scope

- Denial of service via normal trading load
- Social engineering
- Physical access attacks

## Security Practices

- Pre-trade risk validation on every order
- Kill switch for emergency halt
- Input validation on all API endpoints
- No secrets in repository (use `.env` files)
- Dependency scanning via GitHub Dependabot
