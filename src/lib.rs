use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use seqa_core::api::bam_search::bam_search;
use seqa_core::api::bigbed_search::bigbed_search;
use seqa_core::api::bigwig_search::bigwig_search;
use seqa_core::api::fasta_search::fasta_search;
use seqa_core::api::output_format::OutputFormat;
use seqa_core::api::search_options::SearchOptions;
use seqa_core::api::tabix_search::tabix_search;
use seqa_core::stores::StoreService;
use seqa_core::utils::{format_file_path, get_output_format, parse_coordinates};

/// Query a genomic file and return matching lines as a list of tab-delimited strings.
///
/// Automatically detects the file format and index path from the file extension.
/// Supports BAM, FASTA, VCF, BED, BedGraph, BigWig, BigBed, GFF, and GTF.
///
/// Cloud URIs (s3://, az://, gs://, http(s)://) and local paths are both accepted.
/// Set the relevant environment variables for cloud access before calling.
///
/// Args:
///     file_path: URI or local path to the genomic file.
///     coordinates: Genomic region, e.g. "chr12:1000-2000", "chr12:1000", or "chr12".
///     include_header: Include file header lines in the result (default True).
///     header_only: Return only header lines and skip data records (default False).
///     genome: Reference genome build for chromosome length resolution,
///             e.g. "hg38", "hg19", "grch37", "grch38" (default None).
///
/// Returns:
///     List of result lines as strings.
///
/// Raises:
///     ValueError: If the file path, format, or coordinates are invalid, or the search fails.
#[pyfunction]
#[pyo3(signature = (file_path, coordinates, include_header=true, header_only=false, genome=None))]
fn file_search(
    py: Python<'_>,
    file_path: String,
    coordinates: String,
    include_header: bool,
    header_only: bool,
    genome: Option<String>,
) -> PyResult<Vec<String>> {
    // SearchOptions::new swallows parse/format errors with .unwrap_or — validate
    // upfront so callers still get ValueError on bad paths/extensions/coordinates.
    let normalized_path = format_file_path(&file_path)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    get_output_format(&normalized_path)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    parse_coordinates(&coordinates)
        .map_err(|e| PyValueError::new_err(e.to_string()))?;

    let mut options = SearchOptions::new(&file_path, &coordinates);
    options.include_header = include_header;
    options.header_only = header_only;
    if let Some(g) = genome {
        options.genome = Some(g.to_lowercase());
    }

    let format = options.output_format.clone();

    py.allow_threads(|| -> Result<Vec<String>, String> {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())?;

        let result = rt.block_on(async {
            let store_service = StoreService::from_uri(&file_path)
                .map_err(|e| format!("Invalid path {}: {}", file_path, e))?;

            match format {
                OutputFormat::BAM => bam_search(&store_service, &options).await.map_err(|e| e.to_string()),
                OutputFormat::FASTA => fasta_search(&store_service, &options).await.map_err(|e| e.to_string()),
                OutputFormat::BIGWIG => bigwig_search(&store_service, &options).await.map_err(|e| e.to_string()),
                OutputFormat::BIGBED => bigbed_search(&store_service, &options).await.map_err(|e| e.to_string()),
                _ => tabix_search(&store_service, &options).await.map_err(|e| e.to_string()),
            }
        })?;

        Ok(result.lines)
    })
    .map_err(PyValueError::new_err)
}

/// List objects at a cloud or local directory URI.
///
/// Args:
///     dir_path: Directory URI, e.g. "s3://bucket/prefix/", "gs://bucket/dir/", or a local path.
///
/// Returns:
///     List of (path, last_modified_rfc3339, size_bytes) tuples.
///
/// Raises:
///     ValueError: If the URI is invalid or listing fails.
#[pyfunction]
fn list_dir(py: Python<'_>, dir_path: String) -> PyResult<Vec<(String, String, u64)>> {
    py.allow_threads(|| -> Result<Vec<(String, String, u64)>, String> {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .map_err(|e| e.to_string())?;

        rt.block_on(async {
            let service = StoreService::from_uri(&dir_path)
                .map_err(|e| format!("Invalid path {}: {}", dir_path, e))?;

            let objects = service
                .list_objects(&dir_path)
                .await
                .map_err(|e| format!("Failed to list {}: {}", dir_path, e))?;

            Ok(objects
                .into_iter()
                .map(|meta| {
                    (
                        meta.location.to_string(),
                        meta.last_modified.to_rfc3339(),
                        meta.size,
                    )
                })
                .collect())
        })
    })
    .map_err(|e| PyValueError::new_err(e))
}

#[pymodule]
fn _seqa_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(file_search, m)?)?;
    m.add_function(wrap_pyfunction!(list_dir, m)?)?;
    Ok(())
}