import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.extraction import RawExtractedProduct, RawExtractionResult


logger = get_logger(__name__)

PRICE_RE = re.compile(r"(?:\u20b9|Rs\.?|MRP)\s*[\d,]+", re.IGNORECASE)
ETA_RE = re.compile(r"^\d+\s*(?:min|mins|minute|minutes)$", re.IGNORECASE)
OFFER_RE = re.compile(r"\b(?:off|offer|deal|save)\b", re.IGNORECASE)


class BlinkitProductParser:
    """Extracts raw structured product data from rendered Blinkit HTML."""

    platform = "blinkit"

    def parse_file(self, source_path: Path, *, query: str | None = None) -> RawExtractionResult:
        logger.info("blinkit_parser_read_start path=%s", str(source_path))
        html = source_path.read_text(encoding="utf-8")
        result = self.parse_html(html, source_path=source_path, query=query)
        logger.info(
            "blinkit_parser_read_complete path=%s products=%s",
            str(source_path),
            result.product_count,
        )
        return result

    def parse_html(
        self,
        html: str,
        *,
        source_path: Path,
        query: str | None = None,
    ) -> RawExtractionResult:
        soup = BeautifulSoup(html, "html.parser")
        products: list[RawExtractedProduct] = []
        seen: set[tuple[str, str | None, str | None, str | None]] = set()

        for candidate in self._find_product_cards(soup):
            extracted = self._extract_product(candidate, source_index=len(products) + 1)
            if extracted is None:
                continue

            key = (
                extracted.product_name,
                extracted.quantity,
                extracted.displayed_price,
                extracted.mrp,
            )
            if key in seen:
                continue
            seen.add(key)
            products.append(extracted)

        logger.info("blinkit_parser_products_extracted count=%s", len(products))
        return RawExtractionResult(
            query=query,
            source_path=source_path,
            extracted_at=datetime.now(timezone.utc),
            product_count=len(products),
            products=products,
        )

    def save_result(self, result: RawExtractionResult) -> Path:
        settings = get_settings()
        target_dir = settings.cleaned_data_dir / self.platform
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp = result.extracted_at.strftime("%Y%m%dT%H%M%SZ")
        query_slug = self._slugify(result.query or result.source_path.stem)
        output_path = target_dir / f"{timestamp}_{query_slug}.json"
        output_path.write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(
            "blinkit_parser_output_saved path=%s products=%s",
            str(output_path),
            result.product_count,
        )
        return output_path

    def _find_product_cards(self, soup: BeautifulSoup) -> list[Tag]:
        cards: list[Tag] = []
        for element in soup.find_all(attrs={"role": "button"}):
            if not isinstance(element, Tag):
                continue
            text = self._element_text(element)
            if text == "ADD":
                continue
            if "ADD" not in text:
                continue
            if not PRICE_RE.search(text):
                continue
            cards.append(element)

        logger.info("blinkit_parser_candidate_cards count=%s", len(cards))
        return cards

    def _extract_product(
        self,
        card: Tag,
        *,
        source_index: int,
    ) -> RawExtractedProduct | None:
        tokens = [self._normalize_text(token) for token in card.stripped_strings]
        tokens = [token for token in tokens if token]
        if not tokens:
            return None

        raw_text = " ".join(tokens)
        prices = [token for token in tokens if PRICE_RE.search(token)]
        if not prices:
            return None

        displayed_price = prices[0]
        mrp = prices[1] if len(prices) > 1 else None

        offer_text = None
        eta_index = None
        for index, token in enumerate(tokens):
            if ETA_RE.match(token):
                eta_index = index
                break
            if OFFER_RE.search(token):
                offer_text = token

        content_start = (eta_index + 1) if eta_index is not None else 0
        price_index = tokens.index(displayed_price)
        content_tokens = tokens[content_start:price_index]
        if not content_tokens:
            return None

        product_name = content_tokens[0]
        quantity = content_tokens[1] if len(content_tokens) > 1 else None
        stock_availability = self._extract_stock(tokens)

        return RawExtractedProduct(
            source_index=source_index,
            product_name=product_name,
            displayed_price=displayed_price,
            mrp=mrp,
            quantity=quantity,
            stock_availability=stock_availability,
            offer_text=offer_text,
            raw_text=raw_text,
        )

    def _extract_stock(self, tokens: list[str]) -> str | None:
        joined = " ".join(tokens).lower()
        if "out of stock" in joined:
            return "out_of_stock"
        if "notify" in joined:
            return "unavailable"
        if any(token.upper() == "ADD" for token in tokens):
            return "in_stock"
        return None

    def _element_text(self, element: Tag) -> str:
        return self._normalize_text(element.get_text(" ", strip=True))

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.replace("\xa0", " ").split())

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "query"
