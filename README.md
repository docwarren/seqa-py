# seqa_py

Python library for querying genomic files (BAM, VCF, BED, BigWig, BigBed, FASTA, GFF, GTF) across local and cloud storage. Built on [seqa_core](../seqa-rs/seqa_core) via PyO3.

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
from seqa_py import query_file

lines = query_file("s3://my-bucket/sample.vcf.gz", "chr1:100000-200000")
for line in lines:
    print(line)
```

## `query_file`

```python
query_file(
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

`query_file` raises `ValueError` for invalid paths, unsupported extensions, bad coordinates, or search failures.

---

## Command-line interface

```
seqa_py <file_path> <coordinates> [options]
```

The `seqa_py` command is registered as an entry point by `pyproject.toml`. 
It is only available after the package is installed into the vritual environment.
```bash
uv run maturin develop
uv run seqa_py
```
OR

```bash
uv run maturin develop
source .venv/bin/activate
seqa_py --help
```
then when finished,
```bash
deactivate
```
Do not run `python3 seqa_py/cli.py` directly\
That bypasses the venv and will fail with a `ModuleNotFoundError`.

### Examples
```bash
# Local VCF, no header
seqa_py /data/variants.vcf.gz chr12:1-100000000 --no-header

# S3 BAM
seqa_py s3://my-bucket/sample.bam chr1:100000-100001 --no-header

# BigWig on GCS
seqa_py gs://my-bucket/signal.bw chr4:120000000-140000000

# Header lines only
seqa_py s3://my-bucket/sample.vcf.gz chr1 --header-only

# Whole chromosome with explicit genome build
seqa_py s3://my-bucket/sample.vcf.gz chr1 --genome hg38
```

| Flag | Description |
|---|---|
| `--no-header` | Omit file header lines |
| `--header-only` | Print only header lines |
| `--genome BUILD` | Reference genome build (`hg38`, `hg19`, `grch37`, `grch38`) |

---

## REST API server

```bash
uv run seqa_py_server                          # localhost:8000
uv run seqa_py_server --host 0.0.0.0 --port 5000
uv run seqa_py_server --debug
```

### `GET /`

Health check. Returns `Hello world`.

---

### `POST /search`

Query a genomic file.

**Request body** (JSON):
```json
{
  "path": "s3://my-bucket/sample.vcf.gz",
  "coordinates": "chr1:100000-200000"
}
```

**Response** (`text/plain`): newline-separated result lines, including file headers.

**Errors**:

| Status | Reason |
|---|---|
| `400` | Unsupported file type, missing coordinates, bad path, or invalid coordinates |
| `500` | Unexpected server error |

Error responses are JSON: `{"error": "...", "code": 400}`

---

### `POST /files`

List objects at a cloud or local directory URI.

**Request body** (JSON string):
```json
"s3://my-bucket/my-dir/"
```

**Response** (JSON array):
```json
[
  {
    "path": "my-dir/sample.vcf.gz",
    "lastModified": "2024-11-01T12:00:00+00:00",
    "size": 104857600
  }
]
```

---

### `GET /genes/symbols/<genome>`

List all gene symbols in the database for the given genome build.

```
GET /genes/symbols/grch38
GET /genes/symbols/grch37
```

**Response** (JSON array of strings):
```json
["A1BG", "A2M", "BRCA1", "BRCA2", ...]
```

---

### `GET /genes/coordinates/<genome>/<gene>`

Get genomic coordinates for a gene symbol.

```
GET /genes/coordinates/grch38/BRCA1
```

**Response**:
```json
{
  "gene": "BRCA1",
  "chr": "chr17",
  "begin": 43044295,
  "end": 43125483
}
```

**Errors**: `404` if the genome database or gene symbol is not found.

The gene databases (`grch37-genes.db`, `grch38-genes.db`) are read from the path set by the `SEQA_DATA_DIR` environment variable, defaulting to the bundled databases in `seqa_rocket/src/data/`.

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
