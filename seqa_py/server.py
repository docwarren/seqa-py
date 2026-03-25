"""Flask REST API mirroring the seqa_rocket Rocket server."""

import os
import sqlite3

from flask import Flask, jsonify, request
from flask_cors import CORS

# Path to bundled gene SQLite databases. Override with SEQA_DATA_DIR env var.
_DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../seqa-rs/seqa_rocket/src/data",
)
DATA_DIR = os.environ.get("SEQA_DATA_DIR", os.path.abspath(_DEFAULT_DATA_DIR))

from seqa_py import query_file
from seqa_py._seqa_py import list_dir  # type: ignore[import]

SUPPORTED_EXTENSIONS = (
    ".bam", ".vcf.gz", ".bed.gz", ".bedgraph.gz",
    ".gff.gz", ".fasta", ".fa", ".bigwig", ".bb", ".bigbed", ".bw",
)


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(
        app,
        origins=["http://localhost:5173"],
        methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
        supports_credentials=True,
    )

    def error(message: str, code: int):
        return jsonify({"error": message, "code": code}), code

    @app.get("/")
    def index():
        return "Hello world"

    @app.post("/search")
    def search():
        body = request.get_json(silent=True)
        if not body:
            return error("Invalid JSON", 400)

        path = body.get("path", "")
        coordinates = body.get("coordinates", "")

        if not any(path.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return error("Unsupported file type", 400)
        if not coordinates:
            return error("Missing coordinates", 400)

        try:
            lines = query_file(path, coordinates)
        except ValueError as e:
            return error(str(e), 400)
        except Exception as e:
            return error(str(e), 500)

        return "\n".join(lines), 200, {"Content-Type": "text/plain"}

    @app.post("/files")
    def files():
        dir_path = request.get_json(silent=True)
        if not isinstance(dir_path, str) or not dir_path:
            return error("Expected a JSON string directory path", 400)

        try:
            entries = list_dir(dir_path)
        except ValueError as e:
            return error(str(e), 500)

        return jsonify([
            {"path": path, "lastModified": last_modified, "size": size}
            for path, last_modified, size in entries
        ])

    @app.get("/genes/symbols/<genome>")
    def gene_symbols(genome: str):
        db_path = os.path.join(DATA_DIR, f"{genome.lower()}-genes.db")
        if not os.path.exists(db_path):
            return error(f"Gene database not found for genome: {genome}", 404)
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute("SELECT DISTINCT gene FROM coordinates ORDER BY gene").fetchall()
            conn.close()
        except sqlite3.Error as e:
            return error(f"Database error: {e}", 500)
        return jsonify([row[0] for row in rows])

    @app.get("/genes/coordinates/<genome>/<gene>")
    def gene_coordinates(genome: str, gene: str):
        db_path = os.path.join(DATA_DIR, f"{genome.lower()}-genes.db")
        if not os.path.exists(db_path):
            return error(f"Gene database not found for genome: {genome}", 404)
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT gene, chr, begin, end FROM coordinates WHERE gene = ?", (gene,)
            ).fetchone()
            conn.close()
        except sqlite3.Error as e:
            return error(f"Database error: {e}", 500)
        if row is None:
            return error(f"Gene not found: {gene}", 404)
        return jsonify({"gene": row[0], "chr": row[1], "begin": int(row[2]), "end": int(row[3])})

    @app.errorhandler(404)
    def not_found(e):
        return f"<p>404: Not Found - {request.path}</p>", 404

    return app


def main():
    import argparse

    parser = argparse.ArgumentParser(prog="seqa_py_server", description="seqa_py REST API server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    create_app().run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
