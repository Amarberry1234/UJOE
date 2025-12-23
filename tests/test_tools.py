from pathlib import Path

from uj0e.tools import Fingerprinter, LocalFileTool


def test_chunk_text_overlap():
    text = "abcdefghij"
    chunks = Fingerprinter.chunk_text(text, chunk_size=4, chunk_overlap=2)
    assert chunks[0] == "abcd"
    assert chunks[1].startswith("cd")


def test_local_file_tool_respects_root(tmp_path: Path):
    tool = LocalFileTool(root=tmp_path)
    tool.write("allowed.txt", "hello")
    assert "hello" in tool.read("allowed.txt").output
    outside = tool.read("../evil.txt")
    assert outside.ok is False
