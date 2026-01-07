"""Captive portal detection and authentication service."""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, List
from urllib.parse import urlparse, urlunparse
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


class PortalService:
    """Service for detecting and handling captive portals."""

    # Test endpoints to check for internet connectivity
    CONNECTIVITY_CHECK_URLS = [
        "http://clients3.google.com/generate_204",
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://www.apple.com/library/test/success.html",
        "http://captive.apple.com/hotspot-detect.html",
        "http://www.msftconnecttest.com/redirect",
        "http://www.microsoft.com/fwlink/?LinkId=54841",
    ]

    def __init__(self):
        self.session = None
        self.detected_portal_url = None
        self.is_captive = False

    async def detect_captive_portal(self) -> Dict:
        """Detect if behind a captive portal."""
        result = {
            "has_internet": False,
            "is_captive_portal": False,
            "portal_url": None,
            "portal_info": {}
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # Try multiple endpoints
            for url in self.CONNECTIVITY_CHECK_URLS:
                try:
                    async with self.session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=10),
                        allow_redirects=False,
                        headers={"User-Agent": "Mozilla/5.0 (CaptivePortalDetect)"}
                    ) as response:

                        # Check for 204 No Content (success)
                        if response.status == 204:
                            result["has_internet"] = True
                            logger.info(f"Internet connectivity confirmed via {url}")
                            break

                        # Check for redirect to captive portal
                        elif response.status in (302, 303, 307, 308):
                            location = response.headers.get("Location", "")

                            # Detect if redirect looks like a captive portal
                            if self._is_portal_redirect(location, url):
                                result["is_captive_portal"] = True
                                result["portal_url"] = location
                                result["portal_info"] = self._parse_portal_url(location)
                                logger.info(f"Captive portal detected: {location}")
                                break

                        # Some portals return 200 with specific content
                        elif response.status == 200:
                            content_type = response.headers.get("Content-Type", "")

                            if "html" in content_type:
                                content = await response.text()

                                # Check for common portal indicators
                                if self._is_portal_content(content):
                                    result["is_captive_portal"] = True
                                    result["portal_info"]["detected_via_content"] = True

                                    # Try to extract login form URL
                                    login_url = self._extract_login_url(content, url)
                                    if login_url:
                                        result["portal_url"] = login_url
                                    break

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout checking {url}")
                    continue
                except Exception as e:
                    logger.debug(f"Error checking {url}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Portal detection error: {e}")

        return result

    def _is_portal_redirect(self, location: str, original_url: str) -> bool:
        """Check if redirect is likely a captive portal."""
        try:
            original_domain = urlparse(original_url).netloc
            redirect_domain = urlparse(location).netloc

            # Redirect to different domain
            if redirect_domain != original_domain:
                # Common portal patterns
                portal_indicators = [
                    "login", "portal", "auth", "captive", "hotspot",
                    "splash", "gateway", "welcome", "connect", "access"
                ]

                location_lower = location.lower()
                return any(indicator in location_lower for indicator in portal_indicators)

        except Exception:
            pass

        return False

    def _is_portal_content(self, content: str) -> bool:
        """Check if HTML content indicates a captive portal."""
        portal_indicators = [
            "login", "authenticate", "captive portal", "hotspot",
            "accept terms", "agree to terms", "wifi access",
            "network access", "please log in", "sign in",
            "portal", "authentication required"
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in portal_indicators)

    def _parse_portal_url(self, url: str) -> Dict:
        """Parse portal URL for information."""
        try:
            parsed = urlparse(url)
            return {
                "scheme": parsed.scheme,
                "host": parsed.netloc,
                "path": parsed.path,
                "query": parsed.query,
                "is_https": parsed.scheme == "https"
            }
        except Exception:
            return {}

    def _extract_login_url(self, content: str, base_url: str) -> Optional[str]:
        """Try to extract login form URL from HTML content."""
        try:
            # Look for form actions
            form_pattern = r'<form[^>]*action=["\']([^"\']+)["\']'
            matches = re.findall(form_pattern, content, re.IGNORECASE)

            if matches:
                # Return the first action URL
                action = matches[0]
                if action.startswith("/"):
                    parsed = urlparse(base_url)
                    return f"{parsed.scheme}://{parsed.netloc}{action}"
                elif action.startswith("http"):
                    return action

        except Exception as e:
            logger.debug(f"Error extracting login URL: {e}")

        return None

    async def submit_portal_login(
        self,
        portal_url: str,
        username: str = None,
        password: str = None,
        form_data: Dict = None
    ) -> Dict:
        """Submit login form to captive portal."""

        result = {
            "success": False,
            "message": "",
            "requires_interaction": False
        }

        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            # First, fetch the portal page to get the form
            async with self.session.get(
                portal_url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            ) as response:
                content = await response.text()

            # Try to extract form fields
            form_data = form_data or {}
            if username:
                form_data["username"] = username
                if password:
                    form_data["password"] = password

            # Look for form action URL
            form_action_match = re.search(
                r'<form[^>]*action=["\']([^"\']+)["\']',
                content,
                re.IGNORECASE
            )

            if form_action_match:
                action_url = form_action_match.group(1)

                # Make action URL absolute if needed
                if action_url.startswith("/"):
                    parsed = urlparse(portal_url)
                    action_url = f"{parsed.scheme}://{parsed.netloc}{action_url}"

                # Extract method (default POST)
                method_match = re.search(r'<form[^>]*method=["\']?([\w]+)["\']?', content, re.IGNORECASE)
                method = method_match.group(1).upper() if method_match else "POST"

                # Submit the form
                async with self.session.request(
                    method,
                    action_url,
                    data=form_data if method == "POST" else None,
                    params(form_data) if method == "GET" else None,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
                    allow_redirects=True
                ) as response:
                    # Check if login was successful
                    if response.status == 200:
                        response_content = await response.text()

                        # Check for success indicators
                        if not self._is_portal_content(response_content):
                            result["success"] = True
                            result["message"] = "Login successful"
                        else:
                            result["requires_interaction"] = True
                            result["message"] = "Login may have failed - portal still detected"

                    else:
                        result["message"] = f"Unexpected response: {response.status}"

            else:
                result["requires_interaction"] = True
                result["message"] = "Could not find login form - manual intervention required"

        except Exception as e:
            logger.error(f"Portal login error: {e}")
            result["message"] = str(e)
            result["requires_interaction"] = True

        return result

    async def get_portal_html(self, portal_url: str) -> Optional[str]:
        """Fetch the portal HTML for manual interaction."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            async with self.session.get(
                portal_url,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
            ) as response:
                return await response.text()

        except Exception as e:
            logger.error(f"Error fetching portal HTML: {e}")
            return None

    async def check_internet_after_login(self) -> bool:
        """Check if internet is available after portal login."""
        try:
            # Use a simple connectivity check
            async with self.session.get(
                "http://clients3.google.com/generate_204",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 204
        except Exception:
            return False

    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None


def params(data):
    """Convert dict to URL params string."""
    return "&".join(f"{k}={v}" for k, v in data.items())
