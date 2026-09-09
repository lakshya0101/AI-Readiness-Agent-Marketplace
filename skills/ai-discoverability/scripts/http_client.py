"""HTTP Client with redirect tracking, caching, and safety controls."""

from __future__ import annotations
import urllib.request
import urllib.parse
from urllib.error import HTTPError, URLError
from http.client import HTTPResponse as RawHTTPResponse
import ssl
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TIMEOUT = 10
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; BrandAIDiscoverabilityAuditor/1.0; +https://github.com/lakshya0101/AI-Readiness-Agent-Marketplace)"
MAX_REDIRECTS = 10


class HttpResponse:
    """Encapsulates an HTTP fetch result."""

    def __init__(
        self,
        requested_url: str,
        final_url: str,
        status_code: int,
        redirect_chain: List[Dict[str, Any]],
        headers: Dict[str, str],
        body: bytes,
        error: Optional[str] = None,
    ):
        self.requested_url = requested_url
        self.final_url = final_url
        self.status_code = status_code
        self.redirect_chain = redirect_chain
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.body = body
        self.error = error
        self._text: Optional[str] = None

    @property
    def text(self) -> str:
        if self._text is None:
            try:
                # Attempt utf-8, fallback to latin-1
                self._text = self.body.decode("utf-8", errors="replace")
            except Exception:
                self._text = self.body.decode("latin-1", errors="replace")
        return self._text

    @property
    def content_type(self) -> str:
        ct = self.headers.get("content-type", "")
        return ct.split(";")[0].strip().lower() if ct else ""

    @property
    def content_length(self) -> int:
        cl = self.headers.get("content-length")
        if cl and cl.isdigit():
            return int(cl)
        return len(self.body)

    @property
    def is_https(self) -> bool:
        return self.final_url.lower().startswith("https://")

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        return 500 <= self.status_code < 600

    @property
    def redirect_count(self) -> int:
        return len(self.redirect_chain)


class _TrackingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler tracking redirect chain."""

    def __init__(self):
        super().__init__()
        self.chain: List[Dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({
            "from_url": req.full_url,
            "status_code": code,
            "to_url": newurl,
        })
        if len(self.chain) > MAX_REDIRECTS:
            raise HTTPError(req.full_url, code, f"Exceeded maximum redirect limit of {MAX_REDIRECTS}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpClient:
    """Safe, read-only HTTP client with response caching and redirect tracking."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self.cache: Dict[str, HttpResponse] = {}

    def fetch(self, url: str, follow_redirects: bool = True) -> HttpResponse:
        """
        Performs a GET request to url.
        Uses in-memory cache to prevent duplicate requests to the same URL.
        """
        clean_url = url.split("#")[0].strip()
        if clean_url in self.cache:
            return self.cache[clean_url]

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        req = urllib.request.Request(clean_url, headers=headers)
        redirect_handler = _TrackingRedirectHandler()
        handlers: List[Any] = [redirect_handler]

        # Use unverified context only if system certificates fail in restricted test envs
        ssl_context = ssl.create_default_context()
        handlers.append(urllib.request.HTTPSHandler(context=ssl_context))

        opener = urllib.request.build_opener(*handlers)

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                body = resp.read()
                resp_headers = dict(resp.headers)
                final_url = resp.geturl()
                status_code = resp.status if hasattr(resp, "status") else 200

                response_obj = HttpResponse(
                    requested_url=clean_url,
                    final_url=final_url,
                    status_code=status_code,
                    redirect_chain=redirect_handler.chain,
                    headers=resp_headers,
                    body=body,
                    error=None,
                )
                self.cache[clean_url] = response_obj
                return response_obj

        except HTTPError as e:
            body = b""
            try:
                body = e.read()
            except Exception:
                pass
            headers_dict = dict(e.headers) if hasattr(e, "headers") and e.headers else {}
            response_obj = HttpResponse(
                requested_url=clean_url,
                final_url=clean_url,
                status_code=e.code,
                redirect_chain=redirect_handler.chain,
                headers=headers_dict,
                body=body,
                error=f"HTTP {e.code}: {e.reason}",
            )
            self.cache[clean_url] = response_obj
            return response_obj

        except (URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", str(e))
            response_obj = HttpResponse(
                requested_url=clean_url,
                final_url=clean_url,
                status_code=0,
                redirect_chain=redirect_handler.chain,
                headers={},
                body=b"",
                error=f"Network error: {reason}",
            )
            # Do not cache transient connection failures permanently
            return response_obj

        except Exception as e:
            response_obj = HttpResponse(
                requested_url=clean_url,
                final_url=clean_url,
                status_code=0,
                redirect_chain=redirect_handler.chain,
                headers={},
                body=b"",
                error=f"Unexpected error: {str(e)}",
            )
            return response_obj
