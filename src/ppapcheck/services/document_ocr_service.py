from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass

import fitz
from openai import OpenAI


@dataclass
class OcrPageResult:
    page_number: int
    text: str


@dataclass
class OcrBatchResult:
    pages: list[OcrPageResult]
    warnings: list[str]


OCR_PROMPT = """You are an OCR transcription engine for manufacturing quality documents.
Transcribe the page exactly as visible.
Rules:
- Return plain text only.
- Preserve table rows line-by-line.
- Preserve labels, numbers, tolerances, GD&T-like symbols, cavity labels, and checkbox text when visible.
- Do not summarize.
- Do not invent missing text.
- If a portion is unreadable, omit it rather than guessing."""


class DocumentOcrService:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("PPAPCHECK_OCR_MODEL", "").strip()
        self._client: OpenAI | None = None
        if self.api_key and self.model:
            self._client = OpenAI(api_key=self.api_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def extract_pdf_pages(
        self,
        payload: bytes,
        page_numbers: list[int],
    ) -> OcrBatchResult:
        if not self.enabled:
            return OcrBatchResult(
                pages=[],
                warnings=[
                    "OCR fallback is not configured. Set OPENAI_API_KEY and PPAPCHECK_OCR_MODEL to enable scanned PDF extraction."
                ],
            )

        document = fitz.open(stream=payload, filetype="pdf")
        results: list[OcrPageResult] = []
        warnings: list[str] = []
        try:
            for page_number in page_numbers:
                try:
                    page = document.load_page(page_number - 1)
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    image_bytes = pixmap.tobytes("png")
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                    response = self._client.responses.create(
                        model=self.model,
                        input=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "input_text", "text": OCR_PROMPT},
                                    {
                                        "type": "input_image",
                                        "image_url": f"data:image/png;base64,{image_base64}",
                                    },
                                ],
                            }
                        ],
                    )
                    text = (response.output_text or "").strip()
                    if text:
                        results.append(OcrPageResult(page_number=page_number, text=text))
                    else:
                        warnings.append(f"OCR returned empty text for page {page_number}.")
                except Exception as exc:  # pragma: no cover - network/provider failure
                    warnings.append(f"OCR failed for page {page_number}: {exc}")
        finally:
            document.close()

        return OcrBatchResult(pages=results, warnings=warnings)
