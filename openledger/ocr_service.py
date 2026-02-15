"""
Receipt OCR Service

Two-tier OCR pipeline:
1. Tesseract (fast, free, local) for initial text extraction
2. Sonnet Vision (optional fallback) for structured field extraction

Extracts: merchant name, date, total, tax, line items
"""

import base64
import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import anthropic
from PIL import Image

from openledger.config import settings
from openledger.models import Receipt


class OCRService:
    """Receipt scanning and data extraction."""

    def __init__(self, organization_id: uuid.UUID):
        self.org_id = organization_id
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def process_receipt(
        self,
        file_content: bytes,
        mime_type: str,
        uploaded_by: uuid.UUID,
        save_path: str,
    ) -> Receipt:
        """
        Process a receipt image/PDF and extract structured data.
        
        Pipeline:
        1. Save original file
        2. Run Tesseract OCR for raw text
        3. If configured, use Sonnet Vision for structured extraction
        4. Create Receipt record with extracted data
        """
        # Save file and compute hash
        file_hash = hashlib.sha256(file_content).hexdigest()
        file_path = Path(save_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_content)

        # Step 1: Tesseract OCR
        raw_text = self._tesseract_ocr(file_content, mime_type)

        # Step 2: Structured extraction
        if settings.ocr_engine.value == "sonnet-vision":
            extracted = await self._sonnet_vision_extract(file_content, mime_type)
            engine_used = "sonnet-vision"
        else:
            extracted = self._parse_raw_text(raw_text)
            engine_used = "tesseract"

        # Step 3: Build receipt record
        receipt = Receipt(
            organization_id=self.org_id,
            uploaded_by=uploaded_by,
            file_path=str(file_path),
            file_hash=file_hash,
            mime_type=mime_type,
            merchant_name=extracted.get("merchant_name"),
            transaction_date=extracted.get("date"),
            total_amount=extracted.get("total"),
            tax_amount=extracted.get("tax"),
            currency=extracted.get("currency", "USD"),
            line_items_json=extracted.get("line_items"),
            raw_ocr_text=raw_text,
            ocr_engine_used=engine_used,
            ocr_confidence=Decimal(str(extracted.get("confidence", 0.0))),
            is_processed=True,
        )

        return receipt

    def _tesseract_ocr(self, file_content: bytes, mime_type: str) -> str:
        """Extract raw text using Tesseract."""
        try:
            import pytesseract
            from io import BytesIO

            if mime_type.startswith("image/"):
                image = Image.open(BytesIO(file_content))
                text = pytesseract.image_to_string(image)
                return text.strip()
            else:
                # PDF handling would go here (pdf2image conversion)
                return ""
        except ImportError:
            return "[Tesseract not installed]"
        except Exception as e:
            return f"[OCR Error: {e}]"

    async def _sonnet_vision_extract(
        self, file_content: bytes, mime_type: str
    ) -> dict:
        """
        Use Claude Sonnet's vision capability for structured receipt parsing.
        Much more accurate than regex on Tesseract output.
        """
        b64_content = base64.standard_b64encode(file_content).decode("utf-8")

        # Map MIME types for the API
        media_type = mime_type
        if media_type == "image/jpg":
            media_type = "image/jpeg"

        try:
            response = self.client.messages.create(
                model=settings.sonnet_model,
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": b64_content,
                                },
                            },
                            {
                                "type": "text",
                                "text": """Extract structured data from this receipt image.

Respond with ONLY valid JSON:
{
    "merchant_name": "store/business name",
    "date": "YYYY-MM-DD",
    "total": 0.00,
    "tax": 0.00,
    "subtotal": 0.00,
    "currency": "USD",
    "payment_method": "cash/credit/debit/etc",
    "line_items": [
        {"description": "item name", "quantity": 1, "unit_price": 0.00, "amount": 0.00}
    ],
    "confidence": 0.0 to 1.0
}

If a field cannot be determined, set it to null. Parse ALL line items visible.""",
                            },
                        ],
                    }
                ],
            )

            result = json.loads(response.content[0].text)

            # Convert date string to date object
            if result.get("date"):
                try:
                    result["date"] = date.fromisoformat(result["date"])
                except ValueError:
                    result["date"] = None

            # Convert amounts to Decimal
            for field in ["total", "tax", "subtotal"]:
                if result.get(field) is not None:
                    result[field] = Decimal(str(result[field]))

            return result

        except Exception as e:
            return {"confidence": 0.0, "error": str(e)}

    def _parse_raw_text(self, raw_text: str) -> dict:
        """
        Fallback: parse Tesseract output with regex patterns.
        Less accurate than Sonnet but works offline.
        """
        import re

        result = {
            "merchant_name": None,
            "date": None,
            "total": None,
            "tax": None,
            "confidence": 0.3,  # Low confidence for regex parsing
            "line_items": [],
        }

        lines = raw_text.strip().split("\n")

        # Merchant is typically the first non-empty line
        for line in lines:
            line = line.strip()
            if line and len(line) > 2:
                result["merchant_name"] = line
                break

        # Find total
        total_patterns = [
            r'(?:total|amount due|grand total)[:\s]*\$?([\d,]+\.?\d*)',
            r'\$?([\d,]+\.\d{2})\s*(?:total)',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result["total"] = Decimal(match.group(1).replace(",", ""))
                break

        # Find tax
        tax_patterns = [
            r'(?:tax|sales tax|hst|gst)[:\s]*\$?([\d,]+\.?\d*)',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                result["tax"] = Decimal(match.group(1).replace(",", ""))
                break

        # Find date
        date_patterns = [
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
            r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, raw_text)
            if match:
                try:
                    from dateutil import parser as date_parser
                    result["date"] = date_parser.parse(match.group(1)).date()
                except Exception:
                    pass
                break

        return result
