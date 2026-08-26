"""
OpenCaseLaw REST API client for acquiring Swiss Federal Supreme Court decisions.
Official TF (Tribunal Fédéral / Bundesgericht) source via OpenCaseLaw.
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, date
from typing import Optional, Iterator, List, Dict, Any
from urllib.parse import urljoin

import requests


@dataclass
class AcquisitionConfig:
    """Configuration for corpus acquisition."""
    base_url: str = "https://mcp.opencaselaw.ch"
    court: str = "bger"  # Federal Supreme Court (all decisions)
    date_from: str = "2000-01-01"
    date_to: Optional[str] = None
    language: Optional[str] = None  # de, fr, it
    limit_per_request: int = 50
    rate_limit_rps: float = 5.0  # requests per second
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff: float = 2.0


@dataclass
class DecisionRaw:
    """Raw decision from OpenCaseLaw API before normalization."""
    decision_id: str
    court: str
    decision_date: str
    language: str
    title: Optional[str]
    regeste: Optional[str]
    citation_string_de: Optional[str]
    canonical_url: str
    # Additional fields from detail endpoint
    full_text: Optional[str] = None
    legal_area: Optional[str] = None
    chamber: Optional[str] = None
    branch: Optional[str] = None
    proceeding_type: Optional[str] = None
    abstract_de: Optional[str] = None
    abstract_fr: Optional[str] = None
    abstract_it: Optional[str] = None
    outcome: Optional[str] = None
    decision_type: Optional[str] = None
    bge_reference: Optional[str] = None
    cited_decisions: Optional[List[str]] = None
    cited_laws: Optional[List[str]] = None
    judges: Optional[List[str]] = None
    source_url: Optional[str] = None
    pdf_url: Optional[str] = None
    publication_date: Optional[str] = None
    docket_number: Optional[str] = None
    content_hash: Optional[str] = None
    # Structural fields
    sachverhalt: Optional[str] = None
    erwaegungen: Optional[List[Dict[str, Any]]] = None
    dispositiv: Optional[str] = None
    dispositiv_orders: Optional[List[str]] = None
    preparatory_materials: Optional[List[Dict[str, Any]]] = None
    # Citations
    outgoing_citations: Optional[List[Dict[str, Any]]] = None
    incoming_citations: Optional[List[Dict[str, Any]]] = None


@dataclass
class CitationData:
    """Citation data from /api/citations/{decision_id}."""
    decision_id: str
    outgoing: List[Dict[str, Any]]
    incoming: List[Dict[str, Any]]
    total_outgoing: int
    total_incoming: int


class OpenCaseLawClient:
    """Client for OpenCaseLaw REST API with rate limiting and retries."""

    def __init__(self, config: Optional[AcquisitionConfig] = None):
        self.config = config or AcquisitionConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "LexMachina-Corpus/1.0 (+https://github.com/LexMachina/LexMachina)",
            "Accept": "application/json"
        })
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Enforce rate limit between requests."""
        min_interval = 1.0 / self.config.rate_limit_rps
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with exponential backoff retry."""
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                self._last_request_time = time.time()
                response = self.session.request(
                    method, url,
                    timeout=self.config.timeout_seconds,
                    **kwargs
                )
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff ** attempt
                    time.sleep(wait_time)
                else:
                    raise
        raise last_exception

    def search_decisions(
        self,
        q: str = "",
        offset: int = 0,
        limit: Optional[int] = None,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search decisions via /api/decisions endpoint."""
        params = {
            "q": q,
            "offset": offset,
            "limit": limit or self.config.limit_per_request,
        }
        if court:
            params["court"] = court
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if language:
            params["language"] = language

        url = urljoin(self.config.base_url, "/api/decisions")
        response = self._request_with_retry("GET", url, params=params)
        return response.json()

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Fetch full decision detail via /api/decisions/{decision_id}."""
        url = urljoin(self.config.base_url, f"/api/decisions/{decision_id}")
        response = self._request_with_retry("GET", url)
        return response.json()

    def get_decision_structure(self, decision_id: str) -> Dict[str, Any]:
        """Fetch structured decision (Sachverhalt, Erwägungen, Dispositiv, Regeste)."""
        url = urljoin(self.config.base_url, f"/api/structure/{decision_id}")
        response = self._request_with_retry("GET", url)
        return response.json()

    def get_citations(self, decision_id: str, direction: str = "both", limit: int = 1000, offset: int = 0) -> CitationData:
        """Fetch citations for a decision (outgoing, incoming, or both)."""
        url = urljoin(self.config.base_url, f"/api/citations/{decision_id}")
        params = {"direction": direction, "limit": limit, "offset": offset}
        response = self._request_with_retry("GET", url, params=params)
        data = response.json()
        return CitationData(
            decision_id=data["decision_id"],
            outgoing=data.get("outgoing", []),
            incoming=data.get("incoming", []),
            total_outgoing=len(data.get("outgoing", [])),
            total_incoming=len(data.get("incoming", []))
        )

    def get_regeste(self, decision_id: str) -> Dict[str, Any]:
        """Fetch official regeste for a decision."""
        url = urljoin(self.config.base_url, f"/api/regeste/{decision_id}")
        response = self._request_with_retry("GET", url)
        return response.json()

    def get_erwaegung(self, decision_id: str, e_number: str) -> Dict[str, Any]:
        """Fetch a specific Erwägung by number."""
        url = urljoin(self.config.base_url, f"/api/erwaegung/{decision_id}/{e_number}")
        response = self._request_with_retry("GET", url)
        return response.json()

    def iterate_bger_decisions(
        self,
        date_from: str = "2000-01-01",
        date_to: Optional[str] = None,
        language: Optional[str] = None,
        max_decisions: Optional[int] = None,
        include_structure: bool = False,
        include_citations: bool = False
    ) -> Iterator[DecisionRaw]:
        """
        Iterate over all BGer decisions from date_from onward.
        Uses pagination with exact totals via court+date filters.
        """
        offset = 0
        total_fetched = 0
        total_available = None

        while True:
            result = self.search_decisions(
                q="",
                offset=offset,
                limit=self.config.limit_per_request,
                court="bger",
                date_from=date_from,
                date_to=date_to,
                language=language
            )

            if total_available is None:
                total_available = result.get("total", 0)
                print(f"Total BGer decisions matching criteria: {total_available}")

            decisions = result.get("results", [])
            if not decisions:
                break

            for d in decisions:
                if max_decisions and total_fetched >= max_decisions:
                    return

                # Fetch full detail for each decision
                detail = self.get_decision(d["decision_id"])

                # Optionally fetch structure
                structure = None
                if include_structure:
                    try:
                        structure = self.get_decision_structure(d["decision_id"])
                    except Exception as e:
                        print(f"Warning: Failed to fetch structure for {d['decision_id']}: {e}")

                # Optionally fetch citations
                citations = None
                if include_citations:
                    try:
                        citations = self.get_citations(d["decision_id"])
                    except Exception as e:
                        print(f"Warning: Failed to fetch citations for {d['decision_id']}: {e}")

                yield self._parse_decision_detail(d, detail, structure, citations)
                total_fetched += 1

            if not result.get("has_more", False):
                break

            offset = result.get("next_offset", offset + len(decisions))

    def iterate_bger_by_year(
        self,
        start_year: int = 2000,
        end_year: Optional[int] = None,
        language: Optional[str] = None,
        max_decisions_per_year: Optional[int] = None,
        include_structure: bool = False,
        include_citations: bool = False
    ) -> Iterator[DecisionRaw]:
        """
        Iterate over BGer decisions year by year for representative coverage.
        This avoids the relevance-ranking bias of empty queries.
        """
        from datetime import datetime
        if end_year is None:
            end_year = datetime.now().year

        for year in range(start_year, end_year + 1):
            date_from = f"{year}-01-01"
            date_to = f"{year}-12-31"
            print(f"Fetching BGer decisions for year {year}...")
            yield from self.iterate_bger_decisions(
                date_from=date_from,
                date_to=date_to,
                language=language,
                max_decisions=max_decisions_per_year,
                include_structure=include_structure,
                include_citations=include_citations
            )

    def _parse_decision_detail(
        self,
        search_result: Dict,
        detail: Dict,
        structure: Optional[Dict] = None,
        citations: Optional[CitationData] = None
    ) -> DecisionRaw:
        """Parse combined search result + detail + structure + citations into DecisionRaw."""
        # Extract docket number from citation_string_de or decision_id
        docket = detail.get("docket_number") or search_result.get("citation_string_de") or search_result["decision_id"]

        # Compute content hash if full_text available
        full_text = detail.get("full_text") or ""
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest() if full_text else None

        # Extract structural data if available
        sachverhalt = None
        erwaegungen = None
        dispositiv = None
        dispositiv_orders = None
        preparatory_materials = None
        if structure:
            sachverhalt = structure.get("sachverhalt_excerpt")  # excerpt only from structure endpoint
            erwaegungen = structure.get("erwaegungen_paragraphs")
            dispositiv = structure.get("dispositiv")
            dispositiv_orders = structure.get("dispositiv_orders")
            preparatory_materials = structure.get("preparatory_materials")

        # Extract citations if available
        outgoing_citations = None
        incoming_citations = None
        if citations:
            outgoing_citations = citations.outgoing
            incoming_citations = citations.incoming

        return DecisionRaw(
            decision_id=search_result["decision_id"],
            court=search_result["court"],
            decision_date=search_result["decision_date"],
            language=search_result["language"],
            title=search_result.get("title"),
            regeste=detail.get("regeste") or search_result.get("regeste"),
            citation_string_de=search_result.get("citation_string_de"),
            canonical_url=search_result.get("canonical_url"),
            full_text=full_text,
            legal_area=detail.get("legal_area"),
            chamber=detail.get("chamber"),
            branch=detail.get("branch"),
            proceeding_type=detail.get("proceeding_type"),
            abstract_de=detail.get("abstract_de"),
            abstract_fr=detail.get("abstract_fr"),
            abstract_it=detail.get("abstract_it"),
            outcome=detail.get("outcome"),
            decision_type=detail.get("decision_type"),
            bge_reference=detail.get("bge_reference"),
            cited_decisions=detail.get("cited_decisions"),
            cited_laws=detail.get("cited_laws"),
            judges=detail.get("judges"),
            source_url=detail.get("source_url") or search_result.get("canonical_url"),
            pdf_url=detail.get("pdf_url"),
            publication_date=detail.get("publication_date") or search_result.get("publication_date"),
            docket_number=docket,
            content_hash=content_hash,
            sachverhalt=sachverhalt,
            erwaegungen=erwaegungen,
            dispositiv=dispositiv,
            dispositiv_orders=dispositiv_orders,
            preparatory_materials=preparatory_materials,
            outgoing_citations=outgoing_citations,
            incoming_citations=incoming_citations
        )


def download_parquet_dataset(
    output_dir: str = "corpus/acquisition/parquet",
    court: str = "bger",
    force_download: bool = False
) -> str:
    """
    Download the OpenCaseLaw Parquet dataset for a specific court from HuggingFace.
    Returns path to downloaded file.
    """
    import urllib.request

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{court}.parquet"
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path) and not force_download:
        print(f"Parquet file already exists at {output_path}")
        return output_path

    url = f"https://huggingface.co/datasets/voilaj/swiss-caselaw/resolve/main/{court}.parquet"
    print(f"Downloading {court}.parquet from HuggingFace ({url})...")

    def progress_hook(block_num, block_size, total_size):
        if total_size > 0:
            percent = min(100, (block_num * block_size * 100) // total_size)
            if block_num % 100 == 0:
                print(f"  Progress: {percent}% ({block_num * block_size / 1024 / 1024:.1f} MB / {total_size / 1024 / 1024:.1f} MB)")

    try:
        urllib.request.urlretrieve(url, output_path, reporthook=progress_hook)
        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"Downloaded {size_mb:.1f} MB to {output_path}")
        return output_path
    except Exception as e:
        print(f"Failed to download Parquet: {e}")
        raise


def acquire_test_slice(
    output_path: str,
    max_decisions: int = 1000,
    date_from: str = "2000-01-01",
    date_to: Optional[str] = None,
    language: Optional[str] = None,
    include_structure: bool = False,
    include_citations: bool = False
) -> List[DecisionRaw]:
    """
    Acquire a test slice of BGer decisions for reproducible corpus building.
    Returns list of raw decisions and writes JSONL to output_path.
    """
    config = AcquisitionConfig(
        date_from=date_from,
        date_to=date_to,
        language=language
    )
    client = OpenCaseLawClient(config)

    decisions = []
    print(f"Acquiring up to {max_decisions} BGer decisions from {date_from}...")

    for decision in client.iterate_bger_decisions(
        date_from=date_from,
        date_to=date_to,
        language=language,
        max_decisions=max_decisions,
        include_structure=include_structure,
        include_citations=include_citations
    ):
        decisions.append(decision)
        if len(decisions) % 100 == 0:
            print(f"  Fetched {len(decisions)} decisions...")

    # Write JSONL
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(asdict(d), ensure_ascii=False) + "\n")

    print(f"Acquired {len(decisions)} decisions. Written to {output_path}")
    return decisions


def acquire_yearly_slices(
    output_dir: str,
    start_year: int = 2000,
    end_year: Optional[int] = None,
    max_decisions_per_year: Optional[int] = None,
    include_structure: bool = False,
    include_citations: bool = False
) -> Dict[int, List[DecisionRaw]]:
    """
    Acquire BGer decisions year by year for representative coverage.
    Returns dict of year -> list of decisions.
    """
    config = AcquisitionConfig()
    client = OpenCaseLawClient(config)

    all_decisions = {}
    for year in range(start_year, (end_year or datetime.now().year) + 1):
        output_path = os.path.join(output_dir, f"bger_{year}.jsonl")
        decisions = []
        print(f"Acquiring BGer decisions for year {year}...")

        for decision in client.iterate_bger_decisions(
            date_from=f"{year}-01-01",
            date_to=f"{year}-12-31",
            max_decisions=max_decisions_per_year,
            include_structure=include_structure,
            include_citations=include_citations
        ):
            decisions.append(decision)
            if len(decisions) % 100 == 0:
                print(f"  Fetched {len(decisions)} decisions for {year}...")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for d in decisions:
                f.write(json.dumps(asdict(d), ensure_ascii=False) + "\n")

        print(f"Year {year}: acquired {len(decisions)} decisions. Written to {output_path}")
        all_decisions[year] = decisions

    return all_decisions


if __name__ == "__main__":
    # Quick test: acquire 10 decisions
    import sys
    max_d = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    acquire_test_slice(
        output_path="corpus/acquisition/raw/bger_test_slice.jsonl",
        max_decisions=max_d,
        date_from="2024-01-01"  # Recent for quick test
    )