# seqa_py

Python library for querying genomic files (BAM, VCF, BED, BigWig, BigBed, FASTA, GFF, GTF) across local and cloud storage. Built on [seqa_core](https://crates.io/crates/seqa_core) via PyO3.

## Installation

Requires [uv](https://docs.astral.sh/uv/) and a Rust toolchain (rustup).

```bash
git clone <repo>
cd seqa_py
uv run maturin develop   # compile the Rust extension
uv sync --all-groups     # install runtime + dev dependencies (pytest, ruff, maturin)
```

After any change to `src/lib.rs`, re-run `maturin develop`.

## Quick start

```python
from seqa_py import file_search

lines = file_search("s3://my-bucket/sample.vcf.gz", "chr1:100000-200000")
for line in lines:
    print(line)
```

## `file_search`

```python
file_search(
    file_path: str,
    coordinates: str,
    include_header: bool = True,
    header_only: bool = False,
    genome: str | None = None,
) -> list[str]
```

Returns a list of tab-delimited result lines.

| Parameter | Description |
|---|---|
| `file_path` | Local path or cloud URI (`s3://`, `az://`, `gs://`, `https://`) |
| `coordinates` | Genomic region — see formats below |
| `include_header` | Include file header lines in the result (default `True`) |
| `header_only` | Return only header lines, no data records (default `False`) |
| `genome` | Reference build for whole-chromosome length resolution: `hg38`, `hg19`, `grch38`, `grch37` |

### Coordinate formats

| Input | Meaning |
|---|---|
| `chr1:100000-200000` | Range |
| `chr1:100000` | Single position |
| `chr1:100,000-200,000` | Commas ignored |
| `chr1` | Whole chromosome |

### Supported file types

| Extension | Format |
|---|---|
| `.bam` | BAM (requires `.bai` index alongside) |
| `.vcf.gz` | VCF (requires `.tbi` index) |
| `.bed.gz` / `.bed` | BED (requires `.tbi` index) |
| `.bedgraph.gz` | BedGraph (requires `.tbi`) |
| `.gff.gz` | GFF3 (requires `.tbi`) |
| `.gtf.gz` | GTF (requires `.tbi`) |
| `.bw` / `.bigwig` | BigWig (self-indexed) |
| `.bb` / `.bigbed` | BigBed (self-indexed) |
| `.fa` / `.fasta` | FASTA (requires `.fai` index) |

Index files must be at `<file>.<ext>` — e.g. `sample.bam.bai`, `variants.vcf.gz.tbi`. BigWig and BigBed embed their own index and need no companion file.

### Errors

`file_search` raises `ValueError` for invalid paths, unsupported extensions, bad coordinates, or search failures.

---

## Cloud credentials

Set environment variables before querying cloud files. A `.env` file in the working directory is loaded automatically.

**AWS S3**
```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=
S3_BUCKET=
```

**Azure Blob Storage**
```env
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_CONTAINER=
```

**Google Cloud Storage**
```env
GOOGLE_STORAGE_ACCOUNT=
GOOGLE_BUCKET=
```

Copy `.env.example` to `.env` and fill in the values.

---

## Development

```bash
uv run maturin develop          # rebuild Rust extension
uv sync --all-groups            # restore dev dependencies (maturin develop resets the venv)
uv run pytest                   # all tests
uv run pytest tests/test_local.py -v    # local tests only (no cloud creds needed)
uv run ruff check .             # lint
uv run ruff format .            # format
```

Tests in `tests/test_cloud.py` are skipped automatically unless the relevant credentials are present in the environment.

---

## Releasing

Releases are published to PyPI by `.github/workflows/publish.yml`, triggered by pushing a `v*` tag. The workflow builds wheels for Linux (x86_64, aarch64), macOS (universal2), and Windows (x86_64), plus an sdist, then uploads via `maturin upload`.

**One-time setup:** a `pypi` GitHub environment with a `PYPI_API_TOKEN` secret.

**To cut a release:**

1. Bump `version` in `Cargo.toml`. The workflow's `check-version` job fails if the tag and `Cargo.toml` version don't match.
2. Commit the bump.
3. Tag and push:
   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```
4. Watch the `Publish to PyPI` workflow in the Actions tab.

Uploads use `--skip-existing`, so re-running on an already-published version is safe.
