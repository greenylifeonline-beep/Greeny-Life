# BOUND - Absolute Constraints for Greeny-Life EOS
## DANGER ZONES (NEVER TOUCH WITHOUT REVIEW)
- src/master_data/**
- src/finance/**
- src/auth/**
- src/compliance/**
- .env
- config.yaml

## Iron Rules
- All code must pass Bandit security checks.

- All code must pass the SonarQube quality gate.

- At least one human approval is required for withdrawal requests.

- Direct merges on the main branch are not permitted.

- All PRs must have automated documentation generated.

- A backup must be maintained before any automated changes.