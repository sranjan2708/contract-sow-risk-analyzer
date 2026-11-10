"""
Unit and integration tests for doc_engine:
- pdf_reader: extract_pages with 1-based page numbers
- docx_reader: extract_docx_text with sequential reading order
- segmenter: numbered-heading segmentation, section, parent_clause_id, references, deduplication, heading hardening
- parser: parse_document contract compliance, error handling, validation
"""
from __future__ import annotations

from pathlib import Path

import docx
import fitz
import pytest

from doc_engine.docx_reader import extract_docx_text
from doc_engine.parser import parse_document
from doc_engine.pdf_reader import extract_pages
from doc_engine.segmenter import segment
from shared.contracts import DocumentType, ParsedDocument

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SAMPLE_MSA_PDF = FIXTURES_DIR / "sample_msa.pdf"
SAMPLE_SOW_DOCX = FIXTURES_DIR / "sample_sow.docx"


def test_parse_fixture_pdf_clauses_and_references():
    """Fixture PDF -> clause_ids == ['3.1','5.1','8.1','11.2']; 3.1 references 8.1; 11.2 references 14.3."""
    parsed = parse_document(str(SAMPLE_MSA_PDF), "MSA")

    assert isinstance(parsed, ParsedDocument)
    assert parsed.document_id is None
    assert parsed.document_type == DocumentType.MSA
    assert parsed.file_name == "sample_msa.pdf"
    assert parsed.page_count >= 1

    clause_ids = [clause.clause_id for clause in parsed.clauses]
    assert clause_ids == ["3.1", "5.1", "8.1", "11.2"]
    assert all(clause.page_number >= 1 for clause in parsed.clauses)

    clause_3_1 = next(c for c in parsed.clauses if c.clause_id == "3.1")
    assert "8.1" in clause_3_1.references
    assert clause_3_1.section == "3"
    assert clause_3_1.parent_clause_id is None

    clause_5_1 = next(c for c in parsed.clauses if c.clause_id == "5.1")
    assert clause_5_1.references == []
    assert clause_5_1.section == "5"

    clause_8_1 = next(c for c in parsed.clauses if c.clause_id == "8.1")
    assert "3.1" in clause_8_1.references
    assert clause_8_1.section == "8"

    clause_11_2 = next(c for c in parsed.clauses if c.clause_id == "11.2")
    assert "14.3" in clause_11_2.references
    assert clause_11_2.section == "11"


def test_parse_sample_sow_docx_clauses_and_text():
    """sample_sow.docx parses to clauses 2.1 and 4.1 (with the text 'sixty (60) days')."""
    parsed = parse_document(str(SAMPLE_SOW_DOCX), "SOW")

    assert isinstance(parsed, ParsedDocument)
    assert parsed.document_id is None
    assert parsed.document_type == DocumentType.SOW
    assert parsed.file_name == "sample_sow.docx"
    assert parsed.page_count == 1

    clause_ids = [c.clause_id for c in parsed.clauses]
    assert clause_ids == ["2.1", "4.1"]

    c_2_1 = next(c for c in parsed.clauses if c.clause_id == "2.1")
    assert c_2_1.title == "Deliverables"
    assert "deliverables" in c_2_1.text
    assert c_2_1.section == "2"
    assert c_2_1.page_number == 1

    c_4_1 = next(c for c in parsed.clauses if c.clause_id == "4.1")
    assert c_4_1.title == "Fees and Payment"
    assert "sixty (60) days" in c_4_1.text
    assert c_4_1.section == "4"
    assert c_4_1.page_number == 1


def test_body_line_starting_with_section_does_not_create_clause():
    """A body line starting 'Section 8.1 ...' must not create a new clause and its references are extracted."""
    pages = [
        (
            1,
            "3.1 Scope\n"
            "Supplier shall provide the services as agreed.\n"
            "Section 8.1 shall apply to all liability claims.\n"
            "Clause 14.3 governs termination procedures.",
        )
    ]
    clauses = segment(pages)

    assert len(clauses) == 1
    assert clauses[0].clause_id == "3.1"
    assert clauses[0].title == "Scope"
    assert "Section 8.1 shall apply to all liability claims." in clauses[0].text
    assert "8.1" in clauses[0].references
    assert "14.3" in clauses[0].references


def test_parse_txt_path_raises_value_error(tmp_path: Path):
    """Passing a .txt file must raise ValueError for unsupported format."""
    txt_file = tmp_path / "contract.txt"
    txt_file.write_text("Sample contract plain text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_document(str(txt_file), "MSA")


def test_parse_fake_pdf_raises_value_error(tmp_path: Path):
    """A plain text file renamed to .pdf must fail PDF extraction and raise ValueError."""
    fake_pdf = tmp_path / "fake_contract.pdf"
    fake_pdf.write_text("This is not a real PDF file structure", encoding="utf-8")

    with pytest.raises(ValueError, match="Unreadable PDF"):
        parse_document(str(fake_pdf), "MSA")


def test_parse_fake_docx_raises_value_error(tmp_path: Path):
    """A plain text file renamed to .docx must fail DOCX extraction and raise ValueError."""
    fake_docx = tmp_path / "fake_contract.docx"
    fake_docx.write_text("This is not a real DOCX file structure", encoding="utf-8")

    with pytest.raises(ValueError, match="Unreadable DOCX"):
        parse_document(str(fake_docx), "SOW")


def test_parse_nonexistent_file_raises_value_error():
    """Nonexistent file path must raise ValueError."""
    with pytest.raises(ValueError, match="File not found"):
        parse_document("nonexistent_path.pdf", "MSA")


def test_parse_invalid_document_type_raises_value_error():
    """Passing an invalid document_type must raise ValueError."""
    with pytest.raises(ValueError, match="Invalid document_type"):
        parse_document(str(SAMPLE_MSA_PDF), "INVALID_TYPE")


def test_parse_zero_clauses_pdf_raises_value_error(tmp_path: Path):
    """A PDF with pages but zero numbered clauses must raise ValueError."""
    blank_pdf = tmp_path / "empty_contract.pdf"
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    doc.save(str(blank_pdf))
    doc.close()

    with pytest.raises(ValueError, match="Zero clauses found"):
        parse_document(str(blank_pdf), "MSA")


def test_parse_zero_clauses_docx_raises_value_error(tmp_path: Path):
    """A DOCX with paragraphs but zero numbered clauses must raise ValueError."""
    blank_docx = tmp_path / "empty_sow.docx"
    doc = docx.Document()
    doc.add_paragraph("Introductory text without any numbered clause headings.")
    doc.save(str(blank_docx))

    with pytest.raises(ValueError, match="Zero clauses found"):
        parse_document(str(blank_docx), "SOW")


def test_extract_pages_returns_one_based_pages():
    """extract_pages returns sequential 1-based page numbers with non-empty text."""
    pages = extract_pages(str(SAMPLE_MSA_PDF))
    assert len(pages) == 4

    page_nums = [page_num for page_num, _ in pages]
    assert page_nums == [1, 2, 3, 4]

    for page_num, text in pages:
        assert page_num >= 1
        assert len(text.strip()) > 0


def test_extract_pages_nonexistent_file():
    """extract_pages raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        extract_pages("missing_file.pdf")


def test_extract_docx_text_valid_and_nonexistent():
    """extract_docx_text returns [(1, text)] with full text and raises FileNotFoundError if missing."""
    pages = extract_docx_text(str(SAMPLE_SOW_DOCX))
    assert len(pages) == 1
    assert pages[0][0] == 1
    assert "2.1 Deliverables" in pages[0][1]
    assert "sixty (60) days" in pages[0][1]

    with pytest.raises(FileNotFoundError):
        extract_docx_text("missing_file.docx")


def test_segmenter_parent_clause_id_and_section():
    """segment correctly assigns parent_clause_id ('3.1.2' -> '3.1') and section ('3')."""
    pages = [
        (
            1,
            "3.1 Scope\nMain scope text.\n3.1.2 Specific Deliverables\nSub-clause details.\n3.1.2.1 Nested Detail\nDeep detail.",
        )
    ]
    clauses = segment(pages)

    assert len(clauses) == 3

    c1 = clauses[0]
    assert c1.clause_id == "3.1"
    assert c1.section == "3"
    assert c1.parent_clause_id is None

    c2 = clauses[1]
    assert c2.clause_id == "3.1.2"
    assert c2.section == "3"
    assert c2.parent_clause_id == "3.1"

    c3 = clauses[2]
    assert c3.clause_id == "3.1.2.1"
    assert c3.section == "3"
    assert c3.parent_clause_id == "3.1.2"


def test_segmenter_deduplicates_clauses():
    """segment keeps the first occurrence when duplicate clause_ids appear."""
    pages = [
        (1, "3.1 Scope\nFirst occurrence text."),
        (2, "3.1 Scope Redundant\nSecond occurrence text."),
    ]
    clauses = segment(pages)

    assert len(clauses) == 1
    assert clauses[0].clause_id == "3.1"
    assert clauses[0].title == "Scope"
    assert "First occurrence" in clauses[0].text


def test_segmenter_excludes_self_reference():
    """segment excludes a clause's own clause_id from its references list."""
    pages = [
        (
            1,
            "4.2 Termination\nSubject to Section 4.2 and Section 9.1, either party may terminate.",
        )
    ]
    clauses = segment(pages)

    assert len(clauses) == 1
    assert clauses[0].clause_id == "4.2"
    assert "9.1" in clauses[0].references
    assert "4.2" not in clauses[0].references
