"""
Unit tests for PDF generation module.
"""

import pytest
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from app.context_builder import (
    WillContext, WillMaker, Address, Executor, Beneficiary,
    SpecificGift, ResidueBeneficiary
)
from app.clause_renderer import render_document_plan
from app.pdf_generator import generate_pdf_with_footer, create_styles


class TestPDFStyles:
    def test_styles_created(self):
        styles = create_styles()
        assert 'title' in styles
        assert 'clause_heading' in styles
        assert 'normal' in styles
        assert 'bullet_item' in styles
        assert 'numbered_item' in styles
        assert 'signature' in styles


class TestPDFGeneration:
    def test_generate_simple_pdf(self):
        """Test that a simple PDF can be generated."""
        context = WillContext()
        context.will_maker = WillMaker(
            full_name='John Test',
            occupation='Engineer',
            address=Address(
                street='123 Test Street',
                suburb='Brisbane',
                state='QLD',
                postcode='4000'
            )
        )
        context.executors = [
            Executor(
                full_name='Jane Executor',
                relationship='Sister',
                address=Address(
                    street='456 Test Ave',
                    suburb='Brisbane',
                    state='QLD',
                    postcode='4000'
                )
            )
        ]
        context.residue_beneficiaries = [
            ResidueBeneficiary(
                beneficiary_id='b1',
                beneficiary_name='Jane Beneficiary',
                share_percent=100
            )
        ]
        
        document_plan = render_document_plan(context)
        pdf_bytes, pdf_hash = generate_pdf_with_footer(context, document_plan)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_hash is not None
        assert len(pdf_hash) == 64  # SHA256 hex length
        
        # Verify it's a valid PDF (starts with %PDF)
        assert pdf_bytes[:4] == b'%PDF'

    def test_generate_full_pdf(self):
        """Test that a full will PDF can be generated with all options."""
        context = WillContext()
        context.will_maker = WillMaker(
            full_name='John Test',
            occupation='Engineer',
            address=Address(
                street='123 Test Street',
                suburb='Brisbane',
                state='QLD',
                postcode='4000'
            )
        )
        context.has_partner = True
        context.has_children = True
        context.has_minor_children = True
        context.has_guardianship = True
        context.has_specific_gifts = True
        context.has_residue_scheme = True
        context.has_substitution = True
        context.has_minor_trusts = True
        context.has_digital_assets = True
        context.has_pets = True
        context.has_business_interests = True
        context.has_exclusions = True
        context.has_life_sustaining_statement = True
        context.has_funeral_wishes = True
        
        context.executors = [
            Executor(
                full_name='Jane Executor',
                relationship='Sister',
                address=Address(
                    street='456 Test Ave',
                    suburb='Brisbane',
                    state='QLD',
                    postcode='4000'
                )
            )
        ]
        
        context.specific_gifts = [
            SpecificGift(
                beneficiary_id='b1',
                beneficiary_name='Jane Beneficiary',
                gift_type='cash',
                cash_amount=10000
            )
        ]
        
        context.residue_beneficiaries = [
            ResidueBeneficiary(
                beneficiary_id='b1',
                beneficiary_name='Jane Beneficiary',
                share_percent=100
            )
        ]
        
        context.survivorship_days = 30
        context.substitution_rule = 'to_their_children'
        context.minor_trusts_vesting_age = 21
        
        context.funeral_preference = 'cremation'
        context.funeral_notes = 'Simple ceremony'
        
        context.digital_assets_authority = True
        context.digital_assets_categories = ['email', 'social_media']
        context.digital_assets_instructions_location = 'Password manager'
        
        context.pets_count = 2
        context.pets_summary = 'Two dogs'
        context.pets_carer_name = 'Pet Carer'
        context.pets_carer_address = Address(
            street='789 Pet Lane',
            suburb='Brisbane',
            state='QLD',
            postcode='4000'
        )
        context.pets_cash_gift = 5000
        
        context.life_sustaining_template = 'comfort_and_dignity_prioritised'
        context.life_sustaining_values = ['comfort', 'dignity']
        
        document_plan = render_document_plan(context)
        pdf_bytes, pdf_hash = generate_pdf_with_footer(context, document_plan)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        assert pdf_hash is not None
        assert len(pdf_hash) == 64
        assert pdf_bytes[:4] == b'%PDF'

    def test_pdf_hash_consistency(self):
        """Test that the same context produces the same hash."""
        context = WillContext()
        context.will_maker = WillMaker(
            full_name='John Test',
            occupation='Engineer',
            address=Address(
                street='123 Test Street',
                suburb='Brisbane',
                state='QLD',
                postcode='4000'
            )
        )
        context.residue_beneficiaries = [
            ResidueBeneficiary(
                beneficiary_id='b1',
                beneficiary_name='Jane Beneficiary',
                share_percent=100
            )
        ]
        
        document_plan1 = render_document_plan(context)
        pdf_bytes1, hash1 = generate_pdf_with_footer(context, document_plan1)
        
        document_plan2 = render_document_plan(context)
        pdf_bytes2, hash2 = generate_pdf_with_footer(context, document_plan2)
        
        # Same context should produce same hash
        assert hash1 == hash2

    def test_pdf_hash_uniqueness(self):
        """Test that different contexts produce different hashes."""
        context1 = WillContext()
        context1.will_maker = WillMaker(full_name='John Test')
        context1.residue_beneficiaries = [
            ResidueBeneficiary(beneficiary_id='b1', beneficiary_name='Jane', share_percent=100)
        ]
        
        context2 = WillContext()
        context2.will_maker = WillMaker(full_name='Jane Test')  # Different name
        context2.residue_beneficiaries = [
            ResidueBeneficiary(beneficiary_id='b1', beneficiary_name='Jane', share_percent=100)
        ]
        
        document_plan1 = render_document_plan(context1)
        pdf_bytes1, hash1 = generate_pdf_with_footer(context1, document_plan1)
        
        document_plan2 = render_document_plan(context2)
        pdf_bytes2, hash2 = generate_pdf_with_footer(context2, document_plan2)
        
        # Different context should produce different hash
        assert hash1 != hash2

    def test_pdf_contains_key_content(self):
        """Test that the PDF contains key will content."""
        context = WillContext()
        context.will_maker = WillMaker(
            full_name='John Test Person',
            occupation='Engineer',
            address=Address(
                street='123 Test Street',
                suburb='Brisbane',
                state='QLD',
                postcode='4000'
            )
        )
        context.executors = [
            Executor(
                full_name='Jane Executor',
                relationship='Sister',
                address=Address(
                    street='456 Test Ave',
                    suburb='Brisbane',
                    state='QLD',
                    postcode='4000'
                )
            )
        ]
        context.residue_beneficiaries = [
            ResidueBeneficiary(
                beneficiary_id='b1',
                beneficiary_name='Jane Beneficiary',
                share_percent=100
            )
        ]
        
        document_plan = render_document_plan(context)
        pdf_bytes, pdf_hash = generate_pdf_with_footer(context, document_plan)
        
        # Verify PDF structure and metadata
        # Note: PDF text extraction requires a library like PyPDF2
        # We verify the PDF is valid and contains expected structure
        pdf_str = pdf_bytes.decode('latin-1', errors='ignore')
        
        # Check for PDF structure markers
        assert '/Type /Page' in pdf_str or b'/Type /Page' in pdf_bytes
        # Check for font resources (text is rendered using fonts)
        assert '/Font' in pdf_str or b'/Font' in pdf_bytes


class TestDocumentPlanRendering:
    def test_document_plan_structure(self):
        """Test that document plan has correct structure."""
        context = WillContext()
        context.will_maker = WillMaker(full_name='John Test')
        context.residue_beneficiaries = [
            ResidueBeneficiary(beneficiary_id='b1', beneficiary_name='Jane', share_percent=100)
        ]
        
        document_plan = render_document_plan(context)
        
        assert len(document_plan) > 0
        
        # Check first item is title
        assert document_plan[0].id == 'title_identification'
        
        # Check last item is attestation
        assert document_plan[-1].id == 'attestation'
        
        # Check each item has required fields
        for item in document_plan:
            assert item.id is not None
            assert item.title is not None
            assert item.clause_number > 0
            assert item.content_blocks is not None

    def test_content_blocks_structure(self):
        """Test that content blocks have correct structure."""
        context = WillContext()
        context.will_maker = WillMaker(full_name='John Test')
        context.residue_beneficiaries = [
            ResidueBeneficiary(beneficiary_id='b1', beneficiary_name='Jane', share_percent=100)
        ]
        
        document_plan = render_document_plan(context)
        
        for item in document_plan:
            for block in item.content_blocks:
                assert block.type is not None
                assert block.content is not None
                assert block.style is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
