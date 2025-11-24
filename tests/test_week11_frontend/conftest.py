"""Pytest configuration for Week 11 Frontend Tests

Provides Playwright fixtures and configuration for browser testing.
"""
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright


@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Launch arguments for all browser types"""
    return {
        "headless": True,  # Run headless by default, override with --headed
        "slow_mo": 0,      # Slow down execution for debugging (ms)
    }


@pytest.fixture(scope="session")
def browser_context_args():
    """Browser context arguments"""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": False,
        "java_script_enabled": True,
    }


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser in headed mode (visible browser window)"
    )
    parser.addoption(
        "--browser",
        action="store",
        default="chromium",
        help="Browser to use: chromium, firefox, webkit"
    )


@pytest.fixture(scope="session")
def playwright_instance():
    """Create Playwright instance for session"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright, pytestconfig):
    """Launch browser for testing session"""
    browser_name = pytestconfig.getoption("--browser")
    headed = pytestconfig.getoption("--headed")

    browser_type = getattr(playwright_instance, browser_name)

    browser = browser_type.launch(headless=not headed)
    yield browser
    browser.close()


@pytest.fixture
def context(browser: Browser):
    """Create new browser context for each test"""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Playwright Test)",
    )
    yield context
    context.close()


@pytest.fixture
def page(context: BrowserContext):
    """Create new page for each test"""
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def authenticated_page(page: Page):
    """
    Create authenticated page with session cookie.

    Note: This requires actual OAuth login or session injection.
    For now, returns regular page - update when auth is implemented.
    """
    # TODO: Implement session cookie injection
    # For example:
    # page.context.add_cookies([{
    #     "name": "session",
    #     "value": "test-session-token",
    #     "domain": "ai4joy.org",
    #     "path": "/"
    # }])

    return page


@pytest.fixture
def mobile_page(context: BrowserContext):
    """Create page with mobile viewport"""
    context.set_viewport_size({"width": 390, "height": 844})  # iPhone 12
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture
def tablet_page(context: BrowserContext):
    """Create page with tablet viewport"""
    context.set_viewport_size({"width": 768, "height": 1024})  # iPad
    page = context.new_page()
    yield page
    page.close()
