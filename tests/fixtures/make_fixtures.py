"""
Fixture generator for doc_engine and integration tests.
Generates sample_msa.pdf using PyMuPDF and sample_sow.docx using python-docx.
"""
from __future__ import annotations

import logging
from pathlib import Path

import docx
import fitz

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent

MSA_CLAUSES = [
    (
        "3.1 Scope",
        "Supplier shall provide the Services described in each Statement of Work, subject to Section 8.1.",
    ),
    (
        "5.1 Payment Terms",
        "Customer shall pay all undisputed invoices within thirty (30) days of receipt.",
    ),
    (
        "8.1 Limitation of Liability",
        "Notwithstanding Section 3.1, Supplier's total liability shall be unlimited for all claims arising under this Agreement.",
    ),
    (
        "11.2 Termination for Convenience",
        "Customer may terminate this Agreement for convenience upon fifteen (15) days written notice, as described in Section 14.3.",
    ),
]

SOW_CLAUSES = [
    (
        "2.1 Deliverables",
        "Supplier shall deliver the deliverables and perform the services set forth in this Statement of Work.",
    ),
    (
        "4.1 Fees and Payment",
        "Customer shall pay each invoice within sixty (60) days of receipt.",
    ),
]


def generate_sample_msa_pdf(output_path: Path) -> Path:
    """
    Generate sample_msa.pdf with clauses on distinct pages using PyMuPDF.

    Args:
        output_path: Destination file path for sample_msa.pdf.

    Returns:
        Path to the generated PDF file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    for heading, body in MSA_CLAUSES:
        page = doc.new_page(width=595, height=842)  # A4 size
        text = f"{heading}\n{body}"
        rect = fitz.Rect(54, 54, 540, 780)
        page.insert_textbox(rect, text, fontsize=11)

    doc.save(str(output_path))
    doc.close()
    logger.info("Generated sample MSA PDF at %s", output_path)
    return output_path


def generate_sample_sow_docx(output_path: Path) -> Path:
    """
    Generate sample_sow.docx with clauses using python-docx.

    Args:
        output_path: Destination file path for sample_sow.docx.

    Returns:
        Path to the generated DOCX file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = docx.Document()

    for heading, body in SOW_CLAUSES:
        doc.add_heading(heading, level=2)
        doc.add_paragraph(body)

    doc.save(str(output_path))
    logger.info("Generated sample SOW DOCX at %s", output_path)
    return output_path


def generate_all_fixtures() -> tuple[Path, Path]:
    """Generate all test fixtures."""
    msa_pdf = generate_sample_msa_pdf(FIXTURES_DIR / "sample_msa.pdf")
    sow_docx = generate_sample_sow_docx(FIXTURES_DIR / "sample_sow.docx")
    return msa_pdf, sow_docx


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generate_all_fixtures()
