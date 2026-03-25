import argparse
import sys

from seqa_py import query_file


def main():
    parser = argparse.ArgumentParser(
        prog="seqa_py",
        description="Query genomic files (BAM, VCF, BED, BigWig, BigBed, FASTA, GFF, GTF).",
    )
    parser.add_argument("file_path", help="File URI or local path (s3://, az://, gs://, https://, or /local/path)")
    parser.add_argument("coordinates", help='Genomic region, e.g. "chr1:100000-200000", "chr1:100000", or "chr1"')
    parser.add_argument("--no-header", action="store_true", help="Exclude file header lines from output")
    parser.add_argument("--header-only", action="store_true", help="Print only header lines")
    parser.add_argument("--genome", metavar="BUILD", help='Reference genome build, e.g. "hg38" or "hg19"')

    args = parser.parse_args()

    try:
        lines = query_file(
            args.file_path,
            args.coordinates,
            include_header=not args.no_header,
            header_only=args.header_only,
            genome=args.genome,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for line in lines:
        print(line)
