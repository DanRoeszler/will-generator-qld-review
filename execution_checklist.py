"""
Execution Checklist PDF Generator

Generates a separate PDF with signing and witnessing instructions.
This helps ensure proper execution of the will.
"""

import io
import hashlib
from datetime import datetime
from typing import Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem
)

from app.context_builder import WillContext
from app.utils import format_brisbane_datetime


# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_LEFT = 25 * mm
MARGIN_RIGHT = 25 * mm
MARGIN_TOP = 20 * mm
MARGIN_BOTTOM = 25 * mm


def create_checklist_styles():
    """Create styles for the checklist document."""
    styles = getSampleStyleSheet()
    
    return {
        'title': ParagraphStyle(
            'ChecklistTitle',
            parent=styles['Heading1'],
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold',
        ),
        'subtitle': ParagraphStyle(
            'ChecklistSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=24,
            fontName='Helvetica',
            textColor=colors.HexColor('#555555'),
        ),
        'heading': ParagraphStyle(
            'ChecklistHeading',
            parent=styles['Heading2'],
            fontSize=14,
            leading=20,
            spaceBefore=20,
            spaceAfter=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a4232'),
        ),
        'normal': ParagraphStyle(
            'ChecklistNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            fontName='Helvetica',
        ),
        'important': ParagraphStyle(
            'ChecklistImportant',
            parent=styles['Normal'],
            fontSize=11,
            leading=17,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#8B0000'),
        ),
        'checklist_item': ParagraphStyle(
            'ChecklistItem',
            parent=styles['Normal'],
            fontSize=11,
            leading=20,
            leftIndent=25,
            firstLineIndent=-25,
            fontName='Helvetica',
        ),
        'footer': ParagraphStyle(
            'ChecklistFooter',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.grey,
        ),
    }


def generate_execution_checklist(context: WillContext, will_hash: str,
                                  generation_timestamp: datetime = None) -> Tuple[bytes, str]:
    """
    Generate an execution checklist PDF.
    
    Args:
        context: The will context
        will_hash: Hash of the associated will document
        generation_timestamp: Stored timestamp for determinism
    
    Returns:
        Tuple of (PDF bytes, SHA256 hash)
    """
    if generation_timestamp is None:
        generation_timestamp = datetime.utcnow()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    
    styles = create_checklist_styles()
    story = []
    
    # Title
    story.append(Paragraph('WILL EXECUTION CHECKLIST', styles['title']))
    story.append(Paragraph(
        'Instructions for Properly Signing and Witnessing Your Will',
        styles['subtitle']
    ))
    story.append(Spacer(1, 20))
    
    # Document reference
    story.append(Paragraph('Document Reference', styles['heading']))
    story.append(Paragraph(
        f'<b>Will Maker:</b> {context.will_maker.full_name}',
        styles['normal']
    ))
    story.append(Paragraph(
        f'<b>Document Hash:</b> {will_hash[:16]}...',
        styles['normal']
    ))
    story.append(Paragraph(
        f'<b>Generated:</b> {format_brisbane_datetime(generation_timestamp)}',
        styles['normal']
    ))
    story.append(Spacer(1, 20))
    
    # Important warning
    story.append(Paragraph('⚠️ IMPORTANT', styles['heading']))
    story.append(Paragraph(
        'Your will is NOT legally valid until it is properly signed and witnessed. '
        'Failure to follow these instructions may result in your will being invalid '
        'or contested.',
        styles['important']
    ))
    story.append(Spacer(1, 20))
    
    # Before signing
    story.append(Paragraph('Before You Sign', styles['heading']))
    before_items = [
        '☐ Read your will completely and carefully',
        '☐ Ensure all names are spelled correctly',
        '☐ Verify all addresses are current and complete',
        '☐ Confirm the distribution matches your intentions',
        '☐ Print the will on plain white A4 paper (do not use pre-printed forms)',
        '☐ Do NOT sign or date the will yet',
        '☐ Arrange for two independent adult witnesses',
    ]
    for item in before_items:
        story.append(Paragraph(item, styles['checklist_item']))
    story.append(Spacer(1, 15))
    
    # Witness requirements
    story.append(Paragraph('Witness Requirements (Queensland)', styles['heading']))
    story.append(Paragraph(
        'Your witnesses MUST meet ALL of the following requirements:',
        styles['normal']
    ))
    witness_items = [
        '☐ Both witnesses must be 18 years or older',
        '☐ Both witnesses must be present at the same time',
        '☐ Witnesses must be mentally competent',
        '☐ Witnesses must watch you sign the will',
        '☐ You must watch both witnesses sign',
        '☐ Each witness must watch the other witness sign',
    ]
    for item in witness_items:
        story.append(Paragraph(item, styles['checklist_item']))
    story.append(Spacer(1, 15))
    
    # Who cannot witness
    story.append(Paragraph('Who CANNOT Witness Your Will', styles['heading']))
    story.append(Paragraph(
        'The following people should NOT witness your will:',
        styles['normal']
    ))
    cannot_items = [
        '☒ Anyone named as a beneficiary in the will',
        '☒ The spouse or partner of any beneficiary',
        '☒ Anyone under 18 years of age',
        '☒ Anyone who is visually impaired (cannot see you sign)',
        '☒ Anyone who does not understand the nature of the document',
    ]
    for item in cannot_items:
        story.append(Paragraph(item, styles['checklist_item']))
    story.append(Spacer(1, 15))
    
    # Signing procedure
    story.append(Paragraph('Signing Procedure', styles['heading']))
    procedure_items = [
        '☐ Print your full name clearly in the will maker section',
        '☐ Sign your name in the presence of both witnesses',
        '☐ Both witnesses must sign in your presence',
        '☐ Each witness must sign in the presence of the other witness',
        '☐ All signatures must be on the same document',
        '☐ Do NOT sign any pages that are blank or incomplete',
        '☐ Date the will on the date of signing (not before)',
    ]
    for item in procedure_items:
        story.append(Paragraph(item, styles['checklist_item']))
    story.append(Spacer(1, 15))
    
    # After signing
    story.append(Paragraph('After Signing', styles['heading']))
    after_items = [
        '☐ Store the original will in a safe, secure location',
        '☐ Do NOT attach anything to the will (staples, paper clips, etc.)',
        '☐ Do NOT write on the will after signing',
        '☐ Tell your executor where the will is stored',
        '☐ Consider giving a copy to your executor',
        '☐ Review your will every 2-3 years or after major life changes',
    ]
    for item in after_items:
        story.append(Paragraph(item, styles['checklist_item']))
    story.append(Spacer(1, 15))
    
    # What the will does not cover
    story.append(Paragraph('What Your Will Does NOT Cover', styles['heading']))
    story.append(Paragraph(
        'The following assets may NOT pass under your will:',
        styles['normal']
    ))
    not_covered = [
        '<b>Superannuation:</b> Contact your super fund to make a binding death nomination',
        '<b>Jointly held property:</b> Usually passes to the surviving joint owner',
        '<b>Assets in trust:</b> Governed by the trust deed, not your will',
        '<b>Life insurance:</b> Paid to nominated beneficiaries',
        '<b>Company shares:</b> May be subject to shareholder agreements',
    ]
    for item in not_covered:
        story.append(Paragraph(f'• {item}', styles['normal']))
    story.append(Spacer(1, 20))
    
    # When to seek legal advice
    story.append(Paragraph('When to Seek Legal Advice', styles['heading']))
    story.append(Paragraph(
        'Consider consulting a solicitor if any of the following apply:',
        styles['normal']
    ))
    advice_items = [
        'You have significant assets or complex financial arrangements',
        'You own a business or have company interests',
        'You have beneficiaries with special needs',
        'You want to exclude a family member who may contest',
        'You have assets in multiple jurisdictions',
        'You are in a blended family situation',
        'You are unsure about any aspect of your will',
    ]
    for item in advice_items:
        story.append(Paragraph(f'• {item}', styles['normal']))
    story.append(Spacer(1, 20))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        'This checklist is for guidance only and does not constitute legal advice.',
        styles['footer']
    ))
    story.append(Paragraph(
        f'Generated: {format_brisbane_datetime(generation_timestamp)}',
        styles['footer']
    ))
    
    # Build PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # Compute hash
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    
    return pdf_bytes, pdf_hash
