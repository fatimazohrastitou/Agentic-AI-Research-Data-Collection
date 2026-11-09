"""Acquire legally open PDFs from OpenAlex-provided URLs.

The function keeps the original public interface and result statuses while
adding landing-page PDF discovery, redirect handling, PDF signature checks,
and safer temporary-file handling. It does not bypass paywalls or access
controls.
"""
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
import re
import time
import requests


class _PDFLinkParser(HTMLParser):
    """Collect likely PDF links from ordinary article landing pages."""

    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "a" and attrs.get("href"):
            href = attrs["href"].strip()
            text = (attrs.get("title") or "").lower()
            rel = (attrs.get("type") or "").lower()
            if href.lower().endswith(".pdf") or "pdf" in text or "pdf" in rel:
                self.links.append(href)
        if tag.lower() == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            content = (attrs.get("content") or "").strip()
            if content and ("citation_pdf_url" in name or "eprints.document_url" in name):
                self.links.insert(0, content)


def _safe_name(article):
    doi = (article.get("doi") or "").split("doi.org/")[-1]
    key = doi or article.get("openalex_id") or article.get("title") or "article"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", key)[:120] + ".pdf"


def _is_pdf_response(response, first_bytes):
    content_type = (response.headers.get("Content-Type") or "").lower()
    # A real PDF should have the PDF signature. Content-Type alone is not enough.
    return first_bytes.startswith(b"%PDF") or (
        "application/pdf" in content_type and first_bytes.lstrip().startswith(b"%PDF")
    )


def _download_pdf(session, url, timeout, max_bytes=80 * 1024 * 1024):
    """Return (content_bytes, final_url, error_status, error_message)."""
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        body = response.content
        if _is_pdf_response(response, body[:1024]):
            if len(body) > max_bytes:
                return None, response.url, "download_failed", "PDF exceeds configured 80 MB limit"
            return body, response.url, None, None

        content_type = (response.headers.get("Content-Type") or "").lower()
        if "html" not in content_type and not body.lstrip().startswith((b"<!doctype html", b"<html", b"<?xml")):
            return None, response.url, "url_did_not_return_pdf", "Response was not a valid PDF or HTML landing page"

        parser = _PDFLinkParser()
        try:
            parser.feed(body.decode(response.encoding or "utf-8", errors="replace"))
        except Exception:
            pass

        # Try distinct candidate links found in the landing page.
        candidates = []
        for link in parser.links:
            candidate = urljoin(response.url, link)
            if candidate not in candidates:
                candidates.append(candidate)

        last_error = "No direct PDF link found on landing page"
        for candidate in candidates[:8]:
            try:
                pdf_response = session.get(candidate, timeout=timeout, allow_redirects=True)
                pdf_response.raise_for_status()
                pdf_body = pdf_response.content
                if _is_pdf_response(pdf_response, pdf_body[:1024]):
                    if len(pdf_body) > max_bytes:
                        last_error = "PDF exceeds configured 80 MB limit"
                        continue
                    return pdf_body, pdf_response.url, None, None
                last_error = "Discovered link did not return a valid PDF"
            except requests.RequestException as exc:
                last_error = str(exc)[:250]
        return None, response.url, "url_did_not_return_pdf", last_error

    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        # Do not retry or bypass forbidden/paywalled resources.
        return None, url, "download_failed", f"HTTP {status}: {str(exc)[:220]}"
    except requests.RequestException as exc:
        return None, url, "download_failed", str(exc)[:300]


def acquire_open_pdfs(articles, destination="data/full_texts", timeout=30):
    """Download openly accessible PDFs; return one result record per article.

    Expected article fields: openalex_id, title, pdf_url, is_oa.
    Existing statuses are retained for compatibility:
    downloaded, no_open_access_pdf_url, url_did_not_return_pdf, download_failed.
    """
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    results = []
    session = requests.Session()
    session.headers.update({
        "User-Agent": "AgenticSystematicReview/2.0 (educational project; open-access retrieval)",
        "Accept": "application/pdf,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    })

    for article in articles:
        url = article.get("pdf_url") if article.get("is_oa") else None
        record = {
            "openalex_id": article.get("openalex_id"),
            "title": article.get("title"),
            "pdf_url": article.get("pdf_url"),
            "status": "not_attempted",
        }

        if not url:
            record["status"] = "no_open_access_pdf_url"
        else:
            path = folder / _safe_name(article)
            content, final_url, error_status, error_message = _download_pdf(
                session, url, timeout
            )
            if content is not None:
                temp_path = path.with_suffix(path.suffix + ".part")
                try:
                    temp_path.write_bytes(content)
                    # Final integrity check before exposing the file as downloaded.
                    with temp_path.open("rb") as handle:
                        signature = handle.read(5)
                    if signature != b"%PDF-":
                        temp_path.unlink(missing_ok=True)
                        record.update({
                            "status": "url_did_not_return_pdf",
                            "error": "Downloaded content failed the PDF signature check",
                        })
                    else:
                        temp_path.replace(path)
                        record.update({
                            "status": "downloaded",
                            "local_pdf_path": str(path),
                            "final_url": final_url,
                            "file_size_bytes": len(content),
                        })
                except OSError as exc:
                    temp_path.unlink(missing_ok=True)
                    record.update({"status": "download_failed", "error": str(exc)[:300]})
            else:
                record["status"] = error_status or "download_failed"
                record["error"] = error_message or "Unknown download error"
                record["final_url"] = final_url

        results.append(record)
        # Small courtesy delay between different article URLs.
        time.sleep(0.25)

    session.close()
    return results
