# Deployment and Demo Outputs

SOAC produces real demo outputs, not placeholders. Every output has an explicit status so there are no silent failures.

## Guaranteed demos

- Android TFLite demo
  - Android Studio project
  - Runnable inference app
  - Model bundled

## Conditional demos

- TensorRT PC demo
  - Generated if a compatible GPU is available
  - Otherwise a stub plus setup guide is produced

## Demo availability contract

Every demo is tagged with a status:

- AVAILABLE
- UNAVAILABLE (with reason)
- GENERATED
- FAILED

Failures are surfaced explicitly with logs and reasons.
