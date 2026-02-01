# Security and Privacy by Design

SOAC is designed as if it will be audited. Security and privacy are built into the compilation workflow, not added later.

## Upload security

- Extension whitelist
- MIME type and magic byte validation
- SHA-256 hashing
- Size limits
- Path traversal protection

## Execution security

- Docker sandbox
- No internet access during compilation
- Temporary directories
- Automatic cleanup

## Privacy

- No telemetry
- No model retention by default
- Per-user isolation
- Cryptographic build attestation (verifiable outputs)
