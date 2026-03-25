"""Cloud integration tests. Skipped unless the relevant credentials are set."""

import os
import pytest

from seqa_py import query_file

has_aws = pytest.mark.skipif(
    not os.getenv("AWS_ACCESS_KEY_ID"), reason="AWS credentials not set"
)
has_azure = pytest.mark.skipif(
    not os.getenv("AZURE_CLIENT_ID"), reason="Azure credentials not set"
)
has_gcs = pytest.mark.skipif(
    not os.getenv("GOOGLE_STORAGE_ACCOUNT"), reason="GCS credentials not set"
)

S3_VCF = "s3://com.gmail.docarw/test_data/NA12877.EVA.vcf.gz"
S3_CNV_VCF = "s3://com.gmail.docarw/test_data/NA12878.gatk.cnv.vcf.gz"
S3_BAM = "s3://com.gmail.docarw/test_data/NA12877.bam"
S3_BIGWIG = "s3://com.gmail.docarw/test_data/density.bw"
S3_BIGBED = "s3://com.soma23.data/hg38/mane.bb"
AZ_VCF = "az://genreblobs/genre-test-data/NA12877.EVA.vcf.gz"
GCS_VCF = "gs://genre_test_bucket/NA12877.EVA.vcf.gz"
HTTP_VCF = "https://s3.us-west-1.amazonaws.com/com.gmail.docarw/test_data/NA12877.EVA.vcf.gz"


class TestS3Vcf:
    @has_aws
    def test_chr1_small_region(self):
        lines = query_file(S3_VCF, "chr1:1-500000", include_header=False)
        assert len(lines) == 14
        assert lines[0].startswith("chr1\t116549\t")

    @has_aws
    def test_chr12(self):
        lines = query_file(S3_VCF, "chr12:1-120000", include_header=False)
        assert len(lines) == 3
        assert lines[0].startswith("chr12\t86886\t")

    @has_aws
    def test_large_region(self):
        lines = query_file(S3_VCF, "chr1:100000000-200000000", include_header=False)
        assert len(lines) == 112930

    @has_aws
    def test_cnv_vcf_chr12(self):
        lines = query_file(S3_CNV_VCF, "chr12:1-100000000", include_header=False)
        assert len(lines) == 250
        assert lines[0].startswith("chr12\t16000\tNA12878_DUP_chr12_1")


class TestS3Bam:
    @has_aws
    def test_bam_search(self):
        lines = query_file(S3_BAM, "chr12:10000000-10000100", include_header=False)
        assert isinstance(lines, list)
        assert len(lines) > 0
        for line in lines:
            assert "\t" in line


class TestS3BigWig:
    @has_aws
    def test_bigwig_search(self):
        lines = query_file(S3_BIGWIG, "chr4:120000000-140000000", include_header=False)
        assert isinstance(lines, list)
        assert len(lines) > 0


class TestS3BigBed:
    @has_aws
    def test_bigbed_search(self):
        lines = query_file(S3_BIGBED, "chr1:1000000-1300000", include_header=False)
        assert isinstance(lines, list)
        assert len(lines) > 0
        # Verify BED coordinate format: chrom, start, end
        for line in lines:
            fields = line.split("\t")
            assert fields[0] == "chr1"
            start = int(fields[1])
            end = int(fields[2])
            assert end > 1000000 and start < 1300000


class TestAzureVcf:
    @has_azure
    def test_vcf_chr1(self):
        lines = query_file(AZ_VCF, "chr1:100000000-200000000", include_header=False)
        assert len(lines) == 112930


class TestGcsVcf:
    @has_gcs
    def test_vcf_chr1(self):
        lines = query_file(GCS_VCF, "chr1:100000000-200000000", include_header=False)
        assert len(lines) == 112930


class TestHttpVcf:
    def test_vcf_chr1(self):
        """HTTP access requires no credentials."""
        lines = query_file(HTTP_VCF, "chr1:100000000-200000000", include_header=False)
        assert len(lines) == 112930
        assert lines[0].startswith("chr1\t100006117\t")
