# SOAC Security Unit - Threat Model & Documentation

## Overview

The **Secure Model Upload & Validation Unit** is the single gateway through which user-submitted AI models can enter the SOAC (Self-Optimizing AI Compiler) system. This security unit implements **defense-in-depth** with multiple validation layers.

## Threat Model

### Attack Vectors Mitigated

| Attack Type | Mitigation | Module |
|------------|------------|--------|
| **Executable Injection** | Magic byte + MIME validation rejects disguised EXE/DLL/ELF | `magic_bytes.py`, `mime.py` |
| **Script Injection** | Explicit blocklist for .py/.js/.sh/.bat extensions | `config.py`, `upload_validator.py` |
| **Path Traversal** | Filename sanitization, pattern detection | `upload_validator.py` |
| **Archive Bombs** | Block all ZIP/RAR/7z/TAR formats | `magic_bytes.py` |
| **Malformed Models** | ONNX checker validates graph structure | `onnx_validator.py` |
| **DoS (Disk Exhaustion)** | 50MB file size limit enforced before save | `upload_validator.py` |
| **MIME Spoofing** | Content-based detection via libmagic, ignore HTTP headers | `mime.py` |
| **Cross-Upload Contamination** | Per-job isolated directories | `upload_validator.py` |

### Trust Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    UNTRUSTED ZONE                       │
│  - HTTP Request (including headers, filename)           │
│  - File content (any bytes possible)                    │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │   secure_save_and_validate()  │
          │   (THE ONLY ENTRY POINT)      │
          └───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    TRUSTED ZONE                         │
│  - Validated file in isolated job directory             │
│  - SHA-256 hash for integrity verification              │
│  - ValidationMetadata with verified properties          │
└─────────────────────────────────────────────────────────┘
```

## Validation Pipeline

The validation runs in strict order, failing fast on cheap checks:

1. **Filename Sanitization** - Remove dangerous chars, check for traversal
2. **Extension Whitelist** - Only `.onnx`, `.h5`, `.hdf5`, `.keras` allowed
3. **Extension Blocklist** - Immediate reject for `.exe`, `.py`, `.zip`, etc.
4. **File Size Check** - ≤50MB, checked before saving
5. **Save to Isolated Directory** - `soac_upload_{job_id}/`
6. **Magic Byte Validation** - Detect disguised executables/archives
7. **MIME Detection** - Content-based type verification via libmagic
8. **Format-Specific Validation** - ONNX graph checker, HDF5 structure
9. **SHA-256 Hash** - Computed for integrity verification

## Usage

```python
from backend.security import secure_save_and_validate, SecurityValidationError

@app.post("/upload")
async def upload_model(file: UploadFile, job_id: str = Query(...)):
    try:
        metadata = await secure_save_and_validate(file, job_id)
        return {
            "status": "validated",
            "hash": metadata.file_hash,
            "format": metadata.model_format,
        }
    except SecurityValidationError as e:
        # ALL security failures caught here
        logger.warning(f"Upload rejected: {e}")
        raise HTTPException(status_code=400, detail=str(e))
```

## Dependencies

- `python-magic-bin` (Windows) or `python-magic` (Linux/macOS)
- `onnx` - ONNX graph validation
- `h5py` - HDF5/Keras file validation
- `fastapi` - UploadFile type support

## Testing

```bash
pytest tests/test_security/ -v
```

All tests are deterministic and run locally without internet access.
