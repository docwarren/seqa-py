from dotenv import load_dotenv

from ._seqa_py import query_file  # type: ignore[import]

load_dotenv()

__all__ = ["query_file"]
