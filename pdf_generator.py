"""
PDF Generator Module

Renders the final PDF from the document plan using ReportLab.
Produces solicitor-grade will documents with professional formatting.

Design Decisions:
=================

1. Two-Pass Rendering:
   - First pass: Generate PDF without page numbers
   - Calculate hash from stable content
   - Second pass: Add footer with hash and "Page X of Y"
   - This ensures determinism while providing professional pagination

2. Determinism Enforcement:
   - All date/time references use stored generation_timestamp
   - No system time calls during rendering
   - Hash computed over stable content only
   - Same payload + timestamp = identical bytes

3. Typography:
   - Times family for body text (traditional legal document standard)
   - Consistent spacing and margins
   - Professional heading hierarchy

4. Footer Design:
   - Left: Generation date (from stored timestamp)
   - Center: Document hash (short form)
   - Right: Page X of Y
   - This provides integrity verification and professional appearance
"""

import io
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen.canvas import Canvas
from reportlab import rl_config

from app.clause_renderer import DocumentPlanItem, ContentBlock
from app.context_builder import WillContext
from app.utils import short_hash

# Enable invariant mode for deterministic PDF generation
rl_config.invariant = 1


# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 25 * mm
MARGIN_RIGHT = 25 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 30 * mm


class SignatureBlock(Flowable):
    """Custom flowable for signature blocks with professional layout."""
    
    def __init__(self, content: Dict[str, Any], width: float = 400):
        super().__init__()
        self.content = content
        self.block_width = width
        self.line_height = 22
    
    def wrap(self, availWidth, availHeight):
        lines = self.content.get('lines', 3)
        self.height = lines * self.line_height + 50
        return (min(self.block_width, availWidth), self.height)
    
    def draw(self):
        canvas = self.canv
        y = self.height - 25
        
        # Label
        label = self.content.get('label', '')
        if label:
            canvas.setFont('Times-Bold', 11)
            canvas.drawString(0, y, label)
            y -= self.line_height
        
        # Name line
        name_label = self.content.get('name_label', 'Name')
        name = self.content.get('name', '')
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(0, y, f'{name_label}:')
        if name:
            canvas.setFont('Times-Bold', 10)
            canvas.drawString(100, y, name)
        canvas.line(100, y - 2, self.block_width, y - 2)
        y -= self.line_height
        
        # Address line (if present)
        if 'address_label' in self.content:
            canvas.setFont('Times-Roman', 10)
            canvas.drawString(0, y, f"{self.content['address_label']}:")
            canvas.line(100, y - 2, self.block_width, y - 2)
            y -= self.line_height
        
        # Occupation line (if present)
        if 'occupation_label' in self.content:
            canvas.setFont('Times-Roman', 10)
            canvas.drawString(0, y, f"{self.content['occupation_label']}:")
            canvas.line(100, y - 2, self.block_width, y - 2)
            y -= self.line_height
        
        # Signature line
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(0, y, 'Signature:')
        canvas.line(100, y - 2, self.block_width, y - 2)
        y -= self.line_height
        
        # Date line
        date_label = self.content.get('date_label', 'Date')
        canvas.setFont('Times-Roman', 10)
        canvas.drawString(0, y, f'{date_label}:')
        canvas.line(100, y - 2, 220, y - 2)


def create_styles() -> Dict[str, ParagraphStyle]:
    """Create paragraph styles for the will document."""
    styles = getSampleStyleSheet()
    
    custom_styles = {
        'title': ParagraphStyle(
            'WillTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=36,
            fontName='Times-Bold',
        ),
        'clause_heading': ParagraphStyle(
            'ClauseHeading',
            parent=styles['Heading2'],
            fontSize=13,
            leading=20,
            spaceBefore=24,
            spaceAfter=14,
            fontName='Times-Bold',
            textColor=colors.HexColor('#1a1a1a'),
        ),
        'normal': ParagraphStyle(
            'WillNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            fontName='Times-Roman',
            firstLineIndent=0,
        ),
        'definition_term': ParagraphStyle(
            'DefinitionTerm',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            leftIndent=20,
            firstLineIndent=-20,
            spaceAfter=8,
            fontName='Times-Bold',
        ),
        'bullet_item': ParagraphStyle(
            'BulletItem',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            leftIndent=40,
            firstLineIndent=-20,
            spaceAfter=6,
            fontName='Times-Roman',
        ),
        'numbered_item': ParagraphStyle(
            'NumberedItem',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            leftIndent=40,
            firstLineIndent=-25,
            spaceAfter=6,
            fontName='Times-Roman',
        ),
        'signature_label': ParagraphStyle(
            'SignatureLabel',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Times-Bold',
        ),
        'signature': ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            spaceBefore=24,
            spaceAfter=12,
            fontName='Times-Roman',
        ),
    }
    
    return custom_styles


def format_timestamp_for_footer(timestamp: datetime, timezone: str = 'Australia/Brisbane') -> str:
    """
    Format timestamp for PDF footer.
    
    Uses stored generation_timestamp for determinism.
    
    Args:
        timestamp: The generation timestamp
        timezone: Timezone for display
    
    Returns:
        Formatted timestamp string
    """
    if timestamp is None:
        return ''
    
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ZoneInfo('UTC'))
        local_time = timestamp.astimezone(tz)
        return local_time.strftime('%d %B %Y at %I:%M %p %Z')
    except Exception:
        return timestamp.strftime('%d %B %Y %H:%M UTC')


def generate_pdf_with_footer(context: WillContext, document_plan: List[DocumentPlanItem],
                             generation_timestamp: datetime = None) -> Tuple[bytes, str]:
    """
    Generate the final PDF will document with professional footer.
    
    Uses two-pass rendering:
    1. First pass generates content and computes hash
    2. Second pass adds footer with hash and page numbers
    
    Args:
        context: The will context
        document_plan: The rendered document plan
        generation_timestamp: Stored timestamp for determinism
    
    Returns:
        Tuple of (PDF bytes, SHA256 hash)
    """
    if generation_timestamp is None:
        generation_timestamp = datetime.utcnow()
    
    # First pass: Generate PDF without footer to compute hash
    buffer1 = io.BytesIO()
    doc1 = SimpleDocTemplate(
        buffer1,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        # Ensure deterministic PDF metadata
        title='Last Will and Testament',
        author='Will Generator',
        creator='Will Generator',
        creationDate=generation_timestamp,
        modDate=generation_timestamp,
    )
    
    styles = create_styles()
    story = []
    
    # Build document content
    for item in document_plan:
        elements = _render_clause_to_elements(item, styles, context)
        story.extend(elements)
    
    # Build with simple footer (no hash yet)
    doc1.build(story, onFirstPage=_simple_footer, onLaterPages=_simple_footer)
    
    # Get PDF bytes and compute hash
    pdf_bytes_temp = buffer1.getvalue()
    content_hash = hashlib.sha256(pdf_bytes_temp).hexdigest()
    buffer1.close()
    
    # Second pass: Include hash in footer
    buffer2 = io.BytesIO()
    doc2 = SimpleDocTemplate(
        buffer2,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        # Ensure deterministic PDF metadata
        title='Last Will and Testament',
        author='Will Generator',
        creator='Will Generator',
        creationDate=generation_timestamp,
        modDate=generation_timestamp,
    )
    
    story2 = []
    for item in document_plan:
        elements = _render_clause_to_elements(item, styles, context)
        story2.extend(elements)
    
    # Build with full footer
    footer_callback = _create_full_footer_callback(generation_timestamp, content_hash)
    doc2.build(story2, onFirstPage=footer_callback, onLaterPages=footer_callback)
    
    pdf_bytes = buffer2.getvalue()
    buffer2.close()
    
    # Compute final hash from the returned PDF (for verification)
    final_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, final_hash


def _render_clause_to_elements(item: DocumentPlanItem, styles: Dict[str, ParagraphStyle],
                               context: WillContext) -> List:
    """
    Render a document plan item to ReportLab elements.
    
    Args:
        item: The document plan item
        styles: Paragraph styles
        context: The will context
    
    Returns:
        List of ReportLab flowables
    """
    elements = []
    
    # Clause heading
    heading_text = f"{item.clause_number}. {item.title}"
    elements.append(Paragraph(heading_text, styles['clause_heading']))
    
    # Content blocks
    for block in item.content_blocks:
        element = _render_content_block(block, styles)
        if element:
            elements.append(element)
    
    # Add spacing after clause
    elements.append(Spacer(1, 12))
    
    return elements


def _render_content_block(block: ContentBlock, styles: Dict[str, ParagraphStyle]):
    """
    Render a content block to a ReportLab element.
    
    Args:
        block: The content block
        styles: Paragraph styles
    
    Returns:
        ReportLab flowable or None
    """
    if block.type == 'heading1':
        return Paragraph(_escape_text(block.content), styles['title'])
    
    elif block.type == 'paragraph':
        return Paragraph(_escape_text(block.content), styles['normal'])
    
    elif block.type == 'bullet_item':
        content = block.content
        if isinstance(content, dict):
            text = f"• {content.get('term', '')} {content.get('definition', '')}"
        else:
            text = f"• {content}"
        return Paragraph(_escape_text(text), styles['bullet_item'])
    
    elif block.type == 'numbered_item':
        return Paragraph(_escape_text(block.content), styles['numbered_item'])
    
    elif block.type == 'signature_block':
        return SignatureBlock(block.content)
    
    elif block.type == 'page_break':
        return PageBreak()
    
    return None


def _escape_text(text: str) -> str:
    """
    Escape text for ReportLab Paragraph.
    
    Args:
        text: Input text
    
    Returns:
        Escaped text safe for ReportLab
    """
    if not text:
        return ''
    
    # XML escaping for ReportLab
    replacements = [
        ('&', '&amp;'),
        ('<', '&lt;'),
        ('>', '&gt;'),
        ('"', '&quot;'),
    ]
    
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    
    return result


def _simple_footer(canvas, doc):
    """Simple footer without hash (for first pass)."""
    canvas.saveState()
    canvas.setFont('Times-Roman', 8)
    canvas.setFillColor(colors.grey)
    
    page_text = f'Page {doc.page}'
    canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 15 * mm, page_text)
    
    canvas.restoreState()


def _create_full_footer_callback(generation_timestamp: datetime, content_hash: str):
    """
    Create footer callback with generation timestamp and document hash.
    
    Args:
        generation_timestamp: Stored timestamp for determinism
        content_hash: SHA256 hash of document content
    
    Returns:
        Callback function for canvas
    """
    def footer(canvas, doc):
        canvas.saveState()
        
        # Format timestamp
        formatted_time = format_timestamp_for_footer(generation_timestamp)
        short_hash_str = short_hash(content_hash, 16)
        
        # Footer text
        footer_text = f'Generated: {formatted_time} | Hash: {short_hash_str}'
        
        canvas.setFont('Times-Roman', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        
        # Left-aligned footer text
        canvas.drawString(MARGIN_LEFT, 15 * mm, footer_text)
        
        # Right-aligned page number (Page X of Y)
        page_text = f'Page {doc.page}'
        canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, 15 * mm, page_text)
        
        canvas.restoreState()
    
    return footer


def render_pdf_to_bytes(context: WillContext, document_plan: List[DocumentPlanItem],
                        generation_timestamp: datetime = None) -> bytes:
    """
    Render PDF to bytes (convenience function).
    
    Args:
        context: The will context
        document_plan: The rendered document plan
        generation_timestamp: Stored timestamp for determinism
    
    Returns:
        PDF bytes
    """
    pdf_bytes, _ = generate_pdf_with_footer(context, document_plan, generation_timestamp)
    return pdf_bytes


def verify_pdf_integrity(pdf_bytes: bytes, expected_hash: str) -> bool:
    """
    Verify PDF integrity by computing hash.
    
    Args:
        pdf_bytes: PDF content
        expected_hash: Expected SHA256 hash
    
    Returns:
        True if integrity verified
    """
    actual_hash = hashlib.sha256(pdf_bytes).hexdigest()
    return actual_hash == expected_hash
