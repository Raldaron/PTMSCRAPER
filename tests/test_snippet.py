import sys
import os
import types

# Ensure package root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Provide a stub PyPDF2 module before importing snippet
stub_pypdf2 = types.ModuleType("PyPDF2")
stub_pypdf2.PdfReader = lambda stream: None
sys.modules.setdefault("PyPDF2", stub_pypdf2)

import ptmscraper.snippet as snip


class DummyPage:
    def __init__(self, text):
        self._text = text

    def extract_text(self):
        return self._text


class DummyResp:
    def __init__(self, content=b''):
        self.content = content


def make_reader(pages_text):
    class DummyReader:
        def __init__(self, _stream):
            self.pages = [DummyPage(t) for t in pages_text]
    return DummyReader


def test_extract_snippet_found(monkeypatch):
    reader_cls = make_reader(["Start Heartland Payroll Services End"])
    monkeypatch.setattr(snip, "PdfReader", reader_cls)

    resp = DummyResp(b'pdfbytes')
    snippet = snip.extract_snippet(resp, context=5)
    assert "Heartland Payroll" in snippet


def test_extract_snippet_not_found(monkeypatch):
    reader_cls = make_reader(["No keywords here"])
    monkeypatch.setattr(snip, "PdfReader", reader_cls)

    resp = DummyResp(b'pdfbytes')
    snippet = snip.extract_snippet(resp)
    assert snippet == ""
