# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

seqa_py is a Python port of [seqa-rs](../seqa-rs) — a library for querying genomic files (BAM, VCF, GFF, BED, BigWig, BigBed, FASTA) across cloud and local storage backends.

## Build & Test Commands

```bash
uv sync                                    # Install Python dependencies
uv run maturin develop                     # Compile Rust extension (required after any src/lib.rs change)
uv run pytest                              # Run all tests
uv run pytest tests/test_local.py -v       # Run local tests (no cloud creds needed)
uv run pytest tests/test_local.py::TestVcfLocal::test_first_line  # Single test
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
```

The Rust extension must be rebuilt (`maturin develop`) any time `src/lib.rs` changes.

## Architecture

### Coordinate System

All genomic formats preserve their native coordinates. Internal canonical format is **0-based half-open** `[begin, end)`. Terminology: always `begin`/`end`, never `start`/`stop`.

| Format | System |
|--------|--------|
| BED, BAM, BigWig | 0-based half-open |
| VCF, GFF, GTF | 1-based closed |

### Extension Layout

- `src/lib.rs` — PyO3 bindings; compiled to `_seqa_py.so` via maturin.
- `seqa_py/__init__.py` — Python wrapper; imports `query_file` from `._seqa_py` (relative). The `module-name = "seqa_py._seqa_py"` setting in `pyproject.toml` ensures maturin installs the extension inside the `seqa_py` package and creates a `seqa_py.pth` editable pointer.
- `seqa_core` is referenced via local path `../seqa-rs/seqa_core` in `Cargo.toml`.

### Storage Layer

File access is cloud-agnostic. `StoreService.from_uri()` auto-detects backend from URL scheme (`s3://`, `az://`, `gs://`, `file://`, `http(s)://`).

### Search Pipeline

Per-format search functions (`bam_search`, `tabix_search`, `fasta_search`, `bigwig_search`, `bigbed_search`) each take a `SearchOptions` object and return a `SearchResult`.

## Environment Variables

Cloud storage and database access require environment variables:
- **S3**: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`
- **Azure**: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_STORAGE_CONTAINER`, `AZURE_STORAGE_ACCOUNT`
- **GCS**: `GOOGLE_STORAGE_ACCOUNT`, `GOOGLE_BUCKET`

## Test Deletion Policy

**Never delete a failing test** to make CI green. Before removing any test, you must:

1. Identify every assertion and code path exercised by the test.
2. Find an existing *passing* test that covers each of those cases — not just "similar" functionality, but the same inputs, the same code path, and equivalent assertions.
3. If full coverage cannot be confirmed, mark the test with `@pytest.mark.skip` and a comment explaining why (e.g., machine-specific path, missing credentials) rather than deleting it.
4. Prefer moving credential-dependent tests to integration test files over removing them.

Silently dropping tests to unblock CI is not acceptable.
