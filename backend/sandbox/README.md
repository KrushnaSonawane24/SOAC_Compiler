# SOAC Sandbox - Security Controls

## Overview

Docker-based sandbox for executing untrusted AI compiler jobs in complete isolation.

## Security Controls

| Control | Implementation | Purpose |
|---------|---------------|---------|
| Network Isolation | `--network=none` | Blocks data exfiltration |
| Read-Only Root | `--read-only` | Prevents persistence |
| Process Limit | `--pids-limit=100` | Blocks fork bombs |
| Memory Limit | `--memory=512m` | Prevents OOM attacks |
| CPU Limit | `--cpus=1.0` | Prevents CPU starvation |
| No Privileges | `--security-opt=no-new-privileges` | No escalation |
| Non-Root | `--user=nobody` | Least privilege |
| tmpfs /tmp | `--tmpfs=/tmp:size=64M` | RAM-backed, auto-cleanup |

## Workspace Mounts

```
/workspace/
├── input/   (read-only)  - Model files
└── output/  (read-write) - Compilation output
```

## Guaranteed Cleanup

Containers are removed on:
- Normal completion
- Execution failure
- Timeout
- Exception
- Process crash (via atexit)

## Usage

```python
from backend.sandbox import run_job_in_sandbox

result = run_job_in_sandbox(
    job_id="job_123",
    command=["python", "compile.py"],
    input_dir=Path("/tmp/job_123/input"),
    output_dir=Path("/tmp/job_123/output"),
    timeout_seconds=60,
)
```

## Requirements

- Docker Desktop (Windows/macOS) or Docker Engine (Linux)
- Docker Python SDK: `pip install docker`
