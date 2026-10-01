# Wheel content delta / Wheel 产物差异

```sh
wheel-delta before.whl after.whl --html report.html --json report.json
```

Same distribution name required (normalized case/hyphen/dot/underscore). SHA-256 fingerprints
compare bytes, not timestamps. `dist-info` and matching `.data` directory version prefixes normalize
to placeholders. METADATA/RECORD churn is labelled metadata and included, not hidden.
Output lists added/removed/changed paths and sizes, never file contents or absolute input paths.
Findings = changed paths, including expected version metadata. No findings does not prove semantic
compatibility. Only a structurally recognized subset of wheel archives is accepted.

Limits: compressed file 64 MiB; expanded sum 128 MiB; member 32 MiB; 5,000 entries. Duplicate entries,
path traversal, absolute/drive/backslash names, symlinks and encrypted entries reject. No extraction,
installation, package import, RECORD verification or entry-point execution occurs. Corrupt CRC rejects.

只比较字节与路径，不推断 API/ABI 兼容性。资源文件消失可见，但是否应该消失仍由维护者判断。
