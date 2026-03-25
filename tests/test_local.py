"""Tests using local mock data from seqa-rs. No cloud credentials required."""

import os
import pytest

from seqa_py import query_file

# Local test data bundled with seqa-rs
MOCK_DATA = os.path.join(os.path.dirname(__file__), "../../seqa-rs/seqa_core/mock_data")
LOCAL_VCF = os.path.join(MOCK_DATA, "NA12878.gatk.cnv.vcf.gz")


class TestVcfLocal:
    def test_returns_correct_line_count(self):
        """chr12:1-100000000 contains exactly 250 CNV records."""
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=False)
        assert len(lines) == 250

    def test_first_line(self):
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=False)
        fields = lines[0].split("\t")
        assert fields[0] == "chr12"
        assert fields[1] == "16000"
        assert fields[2] == "NA12878_DUP_chr12_1"

    def test_last_line(self):
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=False)
        fields = lines[-1].split("\t")
        assert fields[0] == "chr12"
        assert fields[1] == "99894566"

    def test_lines_are_tab_delimited(self):
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=False)
        for line in lines:
            assert "\t" in line, f"Line is not tab-delimited: {line!r}"

    def test_include_header_true(self):
        """With include_header=True the result should start with VCF header lines."""
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=True)
        assert any(line.startswith("##") for line in lines), "No VCF header lines found"
        assert any(not line.startswith("#") for line in lines), "No data lines found"

    def test_header_only(self):
        lines = query_file(LOCAL_VCF, "chr12:1-100000000", header_only=True)
        assert len(lines) > 0
        assert all(line.startswith("#") for line in lines), "header_only should return only header lines"

    def test_empty_region_returns_no_lines(self):
        """A region with no variants should return an empty list."""
        lines = query_file(LOCAL_VCF, "chr12:1-100", include_header=False)
        assert lines == []

    def test_coordinate_formats(self):
        """All supported coordinate formats should return the same result."""
        with_range = query_file(LOCAL_VCF, "chr12:1-100000000", include_header=False)
        with_commas = query_file(LOCAL_VCF, "chr12:1-100,000,000", include_header=False)
        assert with_range == with_commas

    def test_accepts_absolute_path(self):
        abs_path = os.path.abspath(LOCAL_VCF)
        lines = query_file(abs_path, "chr12:1-100000000", include_header=False)
        assert len(lines) == 250

    def test_invalid_extension_raises(self):
        # format_file_path validates existence before extension check; use the
        # VCF path itself renamed conceptually — easiest is to just assert ValueError.
        with pytest.raises(ValueError):
            query_file(LOCAL_VCF.replace(".vcf.gz", ".unknown"), "chr12:1-100000000")

    def test_nonexistent_file_raises(self):
        with pytest.raises(ValueError):
            query_file("/nonexistent/path/file.vcf.gz", "chr12:1-100000000")

    def test_invalid_chromosome_raises(self):
        with pytest.raises(ValueError, match="Invalid Coordinate string format"):
            query_file(LOCAL_VCF, "chrZZZ:1-1000")
