"""
SOAC Security Configuration
===========================

Centralized security constants and configuration values.

WHY CENTRALIZED CONFIG?
    - Single source of truth for security parameters
    - Easy auditing (one file to review)
    - Prevents magic numbers scattered across codebase
    - Enables environment-based overrides if needed

MODIFICATION WARNING:
    Changes to this file directly impact security posture.
    Any modification should be reviewed by security team.
"""

from pathlib import Path
from typing import Final

# =============================================================================
# FILE SIZE LIMITS
# =============================================================================

MAX_FILE_SIZE_BYTES: Final[int] = 50 * 1024 * 1024  # 50 MB
"""
Maximum allowed file size in bytes.

RATIONALE:
    - Most production ONNX models are under 50MB
    - Larger models should use external storage + URL reference
    - Prevents disk exhaustion DoS attacks
    - Prevents memory exhaustion during validation
"""

MAX_FILE_SIZE_MB: Final[int] = 50  # For display purposes

# =============================================================================
# EXTENSION WHITELISTS AND BLOCKLISTS
# =============================================================================

ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".onnx",    # ONNX Runtime models
    ".h5",      # Keras/TensorFlow HDF5 models
    ".hdf5",    # Alternative HDF5 extension
    ".keras",   # Keras native format (TF 2.x)
    ".tflite",  # TensorFlow Lite
    ".zip",     # TensorFlow SavedModel (zipped)
})
"""
Strictly allowed file extensions.

Files with extensions NOT in this set are rejected immediately.
This is a WHITELIST approach - only explicitly allowed extensions pass.
"""

BLOCKED_EXTENSIONS: Final[frozenset[str]] = frozenset({
    # Executables
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".com", ".msi", ".app", ".deb", ".rpm",
    
    # Scripts
    ".py", ".pyw", ".pyc", ".pyo",
    ".js", ".jsx", ".ts", ".tsx",
    ".sh", ".bash", ".zsh", ".fish",
    ".bat", ".cmd", ".ps1", ".psm1",
    ".rb", ".php", ".pl", ".lua",
    ".vbs", ".vbe", ".wsf", ".wsh",
    
    # Web content (XSS risk)
    ".html", ".htm", ".xhtml",
    ".svg",  # Can contain JavaScript
    ".xml",  # XXE attacks
    
    # Archives (zip bombs, nested threats)
    ".rar", ".7z", ".tar", ".gz",
    ".bz2", ".xz", ".lz", ".lzma",
    ".cab", ".iso", ".dmg",
    
    # Documents with macro support
    ".doc", ".docx", ".docm",
    ".xls", ".xlsx", ".xlsm",
    ".ppt", ".pptx", ".pptm",
    ".pdf",  # Can contain JavaScript
    
    # Other dangerous formats
    ".jar", ".war", ".ear",  # Java archives
    ".apk", ".aab",  # Android packages
    ".ipa",  # iOS packages
    ".scr",  # Windows screensaver (executable)
    ".pif",  # Windows program info file
    ".lnk",  # Windows shortcuts
    ".class",  # Java bytecode
})
"""
Explicitly blocked extensions.

Files with these extensions are rejected with a HIGH severity alert.
The presence of these extensions indicates likely malicious intent.
"""

# =============================================================================
# MAGIC BYTES (FILE SIGNATURES)
# =============================================================================

MAGIC_BYTES: Final[dict[str, bytes]] = {
    # HDF5 format (used by Keras .h5 files)
    # Signature: \x89HDF\r\n\x1a\n
    "hdf5": b"\x89HDF\r\n\x1a\n",
    
    # Note: ONNX uses Protocol Buffers, which don't have a fixed magic signature.
    # ONNX validation is done via the onnx library parser instead.
}
"""
Magic byte signatures for file format validation.

These are the EXACT bytes that must appear at the start of valid files.
Used as a secondary check after MIME type detection.
"""

# Dangerous magic bytes that should NEVER appear
BLOCKED_MAGIC_BYTES: Final[dict[str, bytes]] = {
    # Windows executables
    "exe_mz": b"MZ",  # DOS/Windows executable
    
    # Linux executables
    "elf": b"\x7fELF",  # ELF binary
    
    # macOS executables
    "macho_32": b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
    "macho_64": b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit
    "macho_fat": b"\xca\xfe\xba\xbe",  # Universal binary
    
    # Archives (could contain nested threats)
    "zip": b"PK",  # ZIP/JAR/DOCX/etc
    "rar": b"Rar!",  # RAR archive
    "rar5": b"\x52\x61\x72\x21\x1a\x07\x01\x00",  # RAR5
    "7z": b"7z\xbc\xaf\x27\x1c",  # 7-Zip
    "gzip": b"\x1f\x8b",  # GZIP
    "bzip2": b"BZ",  # BZIP2
    "xz": b"\xfd7zXZ",  # XZ
    
    # Java
    "class": b"\xca\xfe\xba\xbe",  # Java class file (same as Mach-O fat!)
    
    # PDF (can contain JavaScript)
    "pdf": b"%PDF",
}
"""
Magic bytes that indicate BLOCKED file types.

If ANY of these signatures are found at the file start, the file is
rejected immediately regardless of extension or MIME type.
"""

# =============================================================================
# MIME TYPE MAPPINGS
# =============================================================================

ALLOWED_MIME_TYPES: Final[dict[str, frozenset[str]]] = {
    ".onnx": frozenset({
        "application/octet-stream",  # Most common for binary files
        "application/x-protobuf",    # Protocol Buffers
        "application/protobuf",      # Alternative protobuf MIME
    }),
    ".h5": frozenset({
        "application/x-hdf5",
        "application/x-hdf",
        "application/octet-stream",
    }),
    ".hdf5": frozenset({
        "application/x-hdf5",
        "application/x-hdf",
        "application/octet-stream",
    }),
    ".keras": frozenset({
        "application/zip",  # Keras native format is actually a ZIP
        "application/octet-stream",
    }),
    ".tflite": frozenset({
        "application/octet-stream",
        "application/x-tflite",
    }),
    ".zip": frozenset({
        "application/zip",
        "application/octet-stream",
    }),
}
"""
Allowed MIME types per extension.

The MIME type is detected via libmagic (content-based), NOT from
HTTP headers which can be spoofed.
"""

BLOCKED_MIME_TYPES: Final[frozenset[str]] = frozenset({
    "application/x-executable",
    "application/x-dosexec",
    "application/x-msdos-program",
    "application/x-msdownload",
    "application/x-sharedlib",
    "application/x-pie-executable",
    "text/x-python",
    "text/x-script.python",
    "text/javascript",
    "application/javascript",
    "text/html",
    "application/xhtml+xml",
    "application/x-sh",
    "application/x-shellscript",
    "application/x-bat",
    "application/x-msdos-batch",
})
"""
MIME types that are ALWAYS blocked regardless of extension.
"""

# =============================================================================
# TEMPORARY DIRECTORY CONFIGURATION
# =============================================================================

TEMP_DIR_PREFIX: Final[str] = "soac_upload_"
"""
Prefix for temporary job directories.

Each upload gets its own isolated directory: soac_upload_{job_id}/
This prevents cross-contamination between concurrent uploads.
"""

TEMP_DIR_BASE: Final[Path | None] = None
"""
Base directory for temp files. None = use system default (tempfile.gettempdir()).

In production, this might be set to a dedicated partition with quotas.
"""

# =============================================================================
# VALIDATION SETTINGS
# =============================================================================

HASH_ALGORITHM: Final[str] = "sha256"
"""
Hash algorithm for file integrity verification.

SHA-256 provides:
    - 256-bit output (64 hex characters)
    - Collision resistance sufficient for file identification
    - Widely supported and audited
"""

HASH_CHUNK_SIZE: Final[int] = 65536  # 64 KB
"""
Chunk size for streaming hash computation.

64KB balances memory usage with I/O efficiency.
Larger chunks = fewer syscalls but more memory.
"""

# ONNX-specific settings
ONNX_LOAD_EXTERNAL_DATA: Final[bool] = False
"""
Whether to load external tensor data when validating ONNX models.

Set to False for security:
    - External data could reference arbitrary files on disk
    - Could be used for path traversal attacks
    - Could cause excessive memory usage
"""

# =============================================================================
# PATH TRAVERSAL DETECTION
# =============================================================================

PATH_TRAVERSAL_PATTERNS: Final[frozenset[str]] = frozenset({
    "..",           # Parent directory
    "./",           # Current directory (could be combined with ..)
    ".\\",          # Windows current directory
    "..\\",         # Windows parent directory
    "%2e%2e",       # URL-encoded ..
    "%2f",          # URL-encoded /
    "%5c",          # URL-encoded \
    "\x00",         # Null byte (truncation attacks)
})
"""
Patterns that indicate path traversal attempts.

If ANY of these appear in a filename, the upload is rejected.
"""

DANGEROUS_FILENAME_CHARS: Final[frozenset[str]] = frozenset({
    "\x00",  # Null byte
    "\n",    # Newline
    "\r",    # Carriage return
    "\t",    # Tab (could affect logging)
    "|",     # Pipe (shell injection)
    ";",     # Semicolon (shell injection) 
    "&",     # Ampersand (shell injection)
    "$",     # Dollar sign (variable expansion)
    "`",     # Backtick (command substitution)
    ">",     # Redirect (shell injection)
    "<",     # Redirect (shell injection)
    "!",     # History expansion
    "*",     # Glob
    "?",     # Glob
    "[",     # Glob
    "]",     # Glob
    "{",     # Brace expansion
    "}",     # Brace expansion
    "~",     # Home directory
    "#",     # Comment (could truncate)
})
"""
Characters that should not appear in filenames.

These characters could be interpreted specially by shells,
logging systems, or other downstream processors.
"""
