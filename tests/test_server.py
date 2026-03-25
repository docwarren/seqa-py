"""Tests for the Flask REST API server."""

import os
import pytest

from seqa_py.server import create_app

MOCK_DATA = os.path.join(os.path.dirname(__file__), "../../seqa-rs/seqa_core/mock_data")
LOCAL_VCF = os.path.abspath(os.path.join(MOCK_DATA, "NA12878.gatk.cnv.vcf.gz"))


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndex:
    def test_hello_world(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.data == b"Hello world"


class TestSearch:
    def test_vcf_returns_data_lines(self, client):
        r = client.post("/search", json={"path": LOCAL_VCF, "coordinates": "chr12:1-100000000"})
        assert r.status_code == 200
        assert r.content_type.startswith("text/plain")
        lines = [l for l in r.data.decode().splitlines() if not l.startswith("#")]
        assert len(lines) == 250
        assert lines[0].startswith("chr12\t16000\t")

    def test_vcf_includes_header_by_default(self, client):
        r = client.post("/search", json={"path": LOCAL_VCF, "coordinates": "chr12:1-100000000"})
        assert r.status_code == 200
        lines = r.data.decode().splitlines()
        assert any(line.startswith("##") for line in lines)

    def test_unsupported_file_type(self, client):
        r = client.post("/search", json={"path": "s3://bucket/file.txt", "coordinates": "chr1:1-1000"})
        assert r.status_code == 400
        assert "Unsupported file type" in r.json["error"]

    def test_missing_coordinates(self, client):
        r = client.post("/search", json={"path": "s3://bucket/file.vcf.gz", "coordinates": ""})
        assert r.status_code == 400
        assert "Missing coordinates" in r.json["error"]

    def test_invalid_json(self, client):
        r = client.post("/search", data="not json", content_type="application/json")
        assert r.status_code == 400

    def test_missing_path_field(self, client):
        r = client.post("/search", json={"coordinates": "chr1:1-1000"})
        assert r.status_code == 400

    def test_nonexistent_file_returns_400(self, client):
        r = client.post("/search", json={"path": "/nonexistent/file.vcf.gz", "coordinates": "chr12:1-100000000"})
        assert r.status_code == 400

    def test_invalid_coordinates_returns_400(self, client):
        r = client.post("/search", json={"path": LOCAL_VCF, "coordinates": "chrZZZ:1-1000"})
        assert r.status_code == 400


class TestGenes:
    def test_symbols_grch38(self, client):
        r = client.get("/genes/symbols/grch38")
        assert r.status_code == 200
        assert isinstance(r.json, list)
        assert len(r.json) > 0
        assert all(isinstance(s, str) for s in r.json)

    def test_symbols_grch37(self, client):
        r = client.get("/genes/symbols/grch37")
        assert r.status_code == 200
        assert len(r.json) > 0

    def test_symbols_unknown_genome(self, client):
        r = client.get("/genes/symbols/hg99")
        assert r.status_code == 404

    def test_coordinates_known_gene(self, client):
        gene = client.get("/genes/symbols/grch38").json[0]
        r = client.get(f"/genes/coordinates/grch38/{gene}")
        assert r.status_code == 200
        coord = r.json
        assert "gene" in coord and "chr" in coord
        assert isinstance(coord["begin"], int)
        assert isinstance(coord["end"], int)
        assert coord["end"] > coord["begin"]

    def test_coordinates_unknown_gene(self, client):
        r = client.get("/genes/coordinates/grch38/FAKEGENE_XYZ")
        assert r.status_code == 404

    def test_coordinates_unknown_genome(self, client):
        r = client.get("/genes/coordinates/hg99/BRCA1")
        assert r.status_code == 404


class TestNotFound:
    def test_404_returns_html(self, client):
        r = client.get("/nonexistent")
        assert r.status_code == 404
        assert b"404" in r.data
