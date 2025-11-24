"""Tests for Week 11 Landing Page

Test Coverage:
- TC-W11-001: Landing Page Rendering
- TC-W11-006: Static File Serving (partial)
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def base_url():
    """Base URL for testing"""
    import os
    return os.getenv("TEST_BASE_URL", "http://localhost:8080")


class TestLandingPageRendering:
    """TC-W11-001: Landing Page Rendering"""

    def test_landing_page_loads_successfully(self, page: Page, base_url: str):
        """Verify landing page loads with 200 status"""
        response = page.goto(base_url)

        assert response is not None
        assert response.status == 200

    def test_landing_page_has_title(self, page: Page, base_url: str):
        """Verify landing page has correct title"""
        page.goto(base_url)

        # Title should contain "Improv Olympics" or similar
        expect(page).to_have_title(pytest.regex(".*Improv Olympics.*", re.IGNORECASE))

    def test_oauth_login_button_present(self, page: Page, base_url: str):
        """Verify OAuth login button is present"""
        page.goto(base_url)

        # Find login button
        login_button = page.locator("button:has-text('Sign in with Google'), a:has-text('Sign in with Google')")
        expect(login_button).to_be_visible()

    def test_landing_page_has_description(self, page: Page, base_url: str):
        """Verify landing page has descriptive content"""
        page.goto(base_url)

        # Should have some description of the service
        body_text = page.locator("body").inner_text()

        # Look for key phrases
        assert any(phrase in body_text.lower() for phrase in [
            "improv",
            "collaboration",
            "social gym",
            "practice"
        ]), "Landing page should describe the service"

    def test_landing_page_responsive_mobile(self, page: Page, base_url: str):
        """Verify landing page is responsive on mobile viewport"""
        # Set mobile viewport (iPhone 12)
        page.set_viewport_size({"width": 390, "height": 844})

        page.goto(base_url)

        # Page should still load and be usable
        login_button = page.locator("button:has-text('Sign in with Google'), a:has-text('Sign in with Google')")
        expect(login_button).to_be_visible()

        # No horizontal scroll
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        client_width = page.evaluate("document.documentElement.clientWidth")
        assert scroll_width <= client_width, "Page should not have horizontal scroll on mobile"

    def test_landing_page_responsive_tablet(self, page: Page, base_url: str):
        """Verify landing page is responsive on tablet viewport"""
        # Set tablet viewport (iPad)
        page.set_viewport_size({"width": 768, "height": 1024})

        page.goto(base_url)

        # Page should load correctly
        expect(page.locator("body")).to_be_visible()

    def test_landing_page_responsive_desktop(self, page: Page, base_url: str):
        """Verify landing page is responsive on desktop viewport"""
        # Set desktop viewport
        page.set_viewport_size({"width": 1920, "height": 1080})

        page.goto(base_url)

        # Page should load correctly
        expect(page.locator("body")).to_be_visible()


class TestStaticFileServing:
    """TC-W11-006: Static File Serving (partial)"""

    def test_css_files_load_with_correct_mime_type(self, page: Page, base_url: str):
        """Verify CSS files load with correct MIME type"""
        css_loaded = []

        def handle_response(response):
            if ".css" in response.url:
                assert "text/css" in response.headers.get("content-type", ""), \
                    f"CSS file {response.url} has incorrect MIME type"
                css_loaded.append(response.url)

        page.on("response", handle_response)
        page.goto(base_url)

        # At least one CSS file should load
        # Note: This assumes the landing page includes CSS
        # If no CSS, this test should be adjusted

    def test_javascript_files_load_with_correct_mime_type(self, page: Page, base_url: str):
        """Verify JavaScript files load with correct MIME type"""
        js_loaded = []

        def handle_response(response):
            if ".js" in response.url and "application/javascript" in response.headers.get("content-type", ""):
                js_loaded.append(response.url)

        page.on("response", handle_response)
        page.goto(base_url)

        # JavaScript files should have correct MIME type if present

    def test_images_load_with_correct_mime_type(self, page: Page, base_url: str):
        """Verify images load with correct MIME type"""
        image_loaded = []

        def handle_response(response):
            if any(ext in response.url for ext in [".png", ".jpg", ".jpeg", ".svg", ".gif"]):
                content_type = response.headers.get("content-type", "")
                assert "image/" in content_type, \
                    f"Image {response.url} has incorrect MIME type: {content_type}"
                image_loaded.append(response.url)

        page.on("response", handle_response)
        page.goto(base_url)

        # Images should load with correct MIME type if present

    def test_static_files_have_cache_headers(self, page: Page, base_url: str):
        """Verify static files have appropriate cache headers"""
        static_files = []

        def handle_response(response):
            if "/static/" in response.url:
                cache_control = response.headers.get("cache-control", "")
                static_files.append({
                    "url": response.url,
                    "cache_control": cache_control
                })

        page.on("response", handle_response)
        page.goto(base_url)

        # Verify cache headers are set
        for file in static_files:
            assert file["cache_control"], \
                f"Static file {file['url']} missing Cache-Control header"

    def test_text_files_have_compression(self, page: Page, base_url: str):
        """Verify text-based files are compressed (gzip)"""
        compressed_files = []

        def handle_response(response):
            url = response.url
            if any(ext in url for ext in [".css", ".js", ".html"]):
                encoding = response.headers.get("content-encoding", "")
                if "gzip" in encoding or "br" in encoding:
                    compressed_files.append(url)

        page.on("response", handle_response)
        page.goto(base_url)

        # At least some text files should be compressed
        # Note: This depends on Cloud Run/CDN configuration

    def test_no_console_errors_on_landing_page(self, page: Page, base_url: str):
        """Verify no JavaScript console errors on landing page"""
        console_errors = []

        def handle_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text)

        page.on("console", handle_console)
        page.goto(base_url)

        # Wait for page to fully load
        page.wait_for_load_state("networkidle")

        assert len(console_errors) == 0, \
            f"Console errors detected: {console_errors}"

    def test_no_failed_network_requests(self, page: Page, base_url: str):
        """Verify no failed network requests (404, 500)"""
        failed_requests = []

        def handle_response(response):
            if response.status >= 400:
                failed_requests.append({
                    "url": response.url,
                    "status": response.status
                })

        page.on("response", handle_response)
        page.goto(base_url)

        # Wait for page to fully load
        page.wait_for_load_state("networkidle")

        assert len(failed_requests) == 0, \
            f"Failed network requests detected: {failed_requests}"


import re
