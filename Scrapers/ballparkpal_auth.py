import asyncio
import email
import imaplib
import os
import re
import time
from contextlib import asynccontextmanager
from email.utils import parsedate_to_datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright


load_dotenv(Path(__file__).with_name(".env"))

SCRIPT_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = SCRIPT_DIR / "playwright_user_data"
STORAGE_STATE_PATH = SCRIPT_DIR / "ballparkpal_storage_state.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
DEFAULT_TARGET_URL = "https://www.ballparkpal.com/Game-Simulations.php"
LOGIN_URL = "https://www.ballparkpal.com/LoginWithCode.php"
DEBUG_HTML_PATH = SCRIPT_DIR / "data" / "ballparkpal_login_debug.html"

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


@asynccontextmanager
async def ballparkpal_browser_context(playwright, headless=False):
    browser = await playwright.chromium.launch(headless=headless)
    context_options = {"user_agent": USER_AGENT}
    if STORAGE_STATE_PATH.exists():
        context_options["storage_state"] = STORAGE_STATE_PATH

    context = await browser.new_context(**context_options)
    try:
        yield context
    finally:
        await context.close()
        await browser.close()


async def save_ballparkpal_storage_state(context):
    STORAGE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state = await context.storage_state(path=STORAGE_STATE_PATH)
    cookie_count = len(state.get("cookies", []))
    origin_count = len(state.get("origins", []))
    print(
        "Saved BallparkPal storage state "
        f"({cookie_count} cookies, {origin_count} origins) to {STORAGE_STATE_PATH}"
    )


def is_logged_in_html(html):
    html_lower = (html or "").lower()
    return any(
        marker in html_lower
        for marker in (
            "sign out",
            "logout.php",
            "mypreferences.php",
            'class="user-action logout"',
            '<i class="fas fa-sign-out-alt"></i>',
        )
    )


def is_auth_gate(url, html):
    url_lower = (url or "").lower()
    html_lower = (html or "").lower()
    if "checkout.php" in url_lower or "login" in url_lower:
        return True
    gate_markers = (
        "secure checkout",
        "checkout-wrapper",
        "whop-checkout",
        "loginwithcode.php",
        'class="user-action login"',
        "> log in<",
    )
    return any(marker in html_lower for marker in gate_markers)


def assert_authenticated_html(url, html, label):
    if is_auth_gate(url, html) and not is_logged_in_html(html):
        raise RuntimeError(
            f"{label} loaded an unauthenticated BallparkPal page "
            f"({url or 'unknown url'}). Run ballparkpal_signin_auto.py first."
        )


def _fetch_latest_verification_code(min_received_ts=None):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise RuntimeError(
            "EMAIL_ADDRESS / EMAIL_PASSWORD are missing from Scrapers/.env"
        )

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    mail.select("inbox")

    try:
        search_patterns = [
            '(FROM "login@ballpark-pal.com" SUBJECT "Ballpark Pal login code")',
            '(FROM "login@ballpark-pal.com")',
            '(FROM "login@mail.ballparkpal.com" SUBJECT "Ballpark Pal login code")',
            '(FROM "login@mail.ballparkpal.com")',
            '(SUBJECT "Ballpark Pal login code")',
            '(FROM "info@dubclub.win" SUBJECT "DubClub Email Verification")',
            '(FROM "info@dubclub.win")',
            '(SUBJECT "verification")',
            '(SUBJECT "security code")',
        ]
        regex_patterns = [
            r"(\d{3}\s?\d{3}) is your ballpark pal login code",
            r"Your one-time security code is (\d+)",
            r"verification code is (\d+)",
            r"security code is (\d+)",
            r"code[: ]+(\d+)",
            r"(\d{6})",
        ]

        for search_pattern in search_patterns:
            status, messages = mail.search(None, search_pattern)
            if status != "OK" or not messages[0]:
                continue

            for email_id in reversed(messages[0].split()):
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                msg = email.message_from_bytes(msg_data[0][1])
                received_at = None
                if msg.get("Date"):
                    try:
                        received_at = parsedate_to_datetime(msg["Date"]).timestamp()
                    except Exception:
                        received_at = None

                if (
                    min_received_ts is not None
                    and received_at is not None
                    and received_at < min_received_ts
                ):
                    continue

                body_parts = []
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_maintype() == "multipart":
                            continue
                        if part.get("Content-Disposition", "").startswith("attachment"):
                            continue
                        if part.get_content_type() in ("text/plain", "text/html"):
                            try:
                                body_parts.append(
                                    part.get_payload(decode=True).decode(errors="ignore")
                                )
                            except Exception:
                                continue
                else:
                    try:
                        body_parts.append(
                            msg.get_payload(decode=True).decode(errors="ignore")
                        )
                    except Exception:
                        pass

                searchable_text = "\n".join(
                    part
                    for part in (
                        msg.get("Subject", ""),
                        "\n".join(body_parts),
                    )
                    if part
                )
                for regex_pattern in regex_patterns:
                    match = re.search(regex_pattern, searchable_text, re.IGNORECASE)
                    if match:
                        return re.sub(r"\s+", "", match.group(1))
        return None
    finally:
        try:
            mail.close()
        except Exception:
            pass
        mail.logout()


async def wait_for_verification_code(timeout_seconds=90, poll_seconds=5):
    min_received_ts = time.time() - 30
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        code = await asyncio.to_thread(_fetch_latest_verification_code, min_received_ts)
        if code:
            return code
        await asyncio.sleep(poll_seconds)
    return None


async def _find_first_visible(page, selectors, timeout=5000):
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            return locator, selector
        except Exception:
            continue
    return None, None


async def _code_inputs(page):
    locator = page.locator(".code-input")
    if await locator.count() >= 6:
        return locator
    locator = page.locator("input[data-index]")
    if await locator.count() >= 6:
        return locator
    return None


async def ensure_logged_in(target_url=DEFAULT_TARGET_URL, headless=False, keep_open=False):
    async with async_playwright() as p:
        async with ballparkpal_browser_context(p, headless=headless) as context:
            page = context.pages[0] if context.pages else await context.new_page()

            try:
                print(f"Checking BallparkPal session at {target_url}...")
                await page.goto(target_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                html = await page.content()

                if not is_auth_gate(page.url, html) or is_logged_in_html(html):
                    print("BallparkPal session already authenticated.")
                    await save_ballparkpal_storage_state(context)
                    return True

                if not EMAIL_ADDRESS:
                    raise RuntimeError("EMAIL_ADDRESS is missing from Scrapers/.env")

                print("Session expired. Refreshing BallparkPal login...")
                await page.goto(LOGIN_URL, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)

                login_with_code_selectors = [
                    "text=Log in with a code",
                    "a:has-text('Log in with a code')",
                    "a:has-text('Login with code')",
                    "text=Log In with Code",
                ]
                link, matched_selector = await _find_first_visible(
                    page, login_with_code_selectors, timeout=1500
                )
                if link:
                    await link.click()
                    print(f"Switched to code-login flow using selector: {matched_selector}")
                    await page.wait_for_timeout(1200)

                code_inputs = await _code_inputs(page)
                if code_inputs:
                    print("Verification code page is already open.")
                    resend_selectors = [
                        "#resendBtn",
                        'button[name="send_code"]',
                        'button:has-text("Resend code")',
                    ]
                    resend_button, matched_selector = await _find_first_visible(
                        page, resend_selectors, timeout=1500
                    )
                    if resend_button:
                        await resend_button.click()
                        print(f"Requested a fresh login code with selector: {matched_selector}")
                        await page.wait_for_timeout(1500)
                else:
                    email_selectors = [
                        'input[placeholder="Your email..."]',
                        'input[placeholder*="email" i]',
                        'input[type="email"]',
                        'input[name="email"]',
                        'input[id*="email" i]',
                        'input[placeholder="Enter your email address"]',
                    ]
                    email_input, matched_selector = await _find_first_visible(page, email_selectors)
                    if not email_input:
                        labeled = page.get_by_label(re.compile("email", re.IGNORECASE)).first
                        try:
                            await labeled.wait_for(state="visible", timeout=5000)
                            email_input = labeled
                            matched_selector = "label=/email/i"
                        except Exception:
                            email_input = None

                    if not email_input:
                        DEBUG_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
                        DEBUG_HTML_PATH.write_text(await page.content(), encoding="utf-8")
                        raise RuntimeError("Could not find the BallparkPal email input.")

                    await email_input.fill(EMAIL_ADDRESS)
                    print(f"Filled login email using selector: {matched_selector}")

                    submit_selectors = [
                        'button:has-text("Continue with Email")',
                        'button:has-text("Send Login Code")',
                        'button:has-text("Send Code")',
                        'button:has-text("Continue")',
                        '[type="submit"]',
                    ]
                    submit_button, matched_selector = await _find_first_visible(
                        page, submit_selectors, timeout=3000
                    )
                    if submit_button:
                        await submit_button.click()
                        print(f"Submitted login email with selector: {matched_selector}")
                    else:
                        print("Login submit button not found; submitting with Enter.")
                        await email_input.press("Enter")

                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_timeout(3000)

                print("Waiting for email verification code...")
                verification_code = await wait_for_verification_code()
                if not verification_code:
                    raise RuntimeError("Timed out waiting for the BallparkPal verification code.")

                code_inputs = await _code_inputs(page)
                if code_inputs:
                    for index, digit in enumerate(verification_code[:6]):
                        await code_inputs.nth(index).fill(digit)
                        await page.wait_for_timeout(50)
                    matched_selector = ".code-input"
                else:
                    otp_selectors = [
                        "input.invisible-input",
                        "input[autocomplete='one-time-code']",
                        "input[inputmode='numeric']",
                        "input[placeholder*='code' i]",
                        "[data-testid='otp-input']",
                        "input[type='text']",
                    ]
                    otp_input, matched_selector = await _find_first_visible(
                        page, otp_selectors, timeout=8000
                    )
                    if not otp_input:
                        DEBUG_HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
                        DEBUG_HTML_PATH.write_text(await page.content(), encoding="utf-8")
                        raise RuntimeError("Could not find the BallparkPal verification code input.")

                    await otp_input.fill("")
                    await otp_input.type(verification_code, delay=75)

                print(f"Entered verification code using selector: {matched_selector}")
                await page.wait_for_timeout(1500)

                verify_selectors = [
                    'button:has-text("Verify Email")',
                    'button:has-text("Verify")',
                    'button:has-text("Submit")',
                    '[type="submit"]',
                ]
                verify_button, matched_selector = await _find_first_visible(
                    page, verify_selectors, timeout=3000
                )
                if verify_button:
                    await verify_button.click()
                    print(f"Clicked verification button with selector: {matched_selector}")
                elif not code_inputs:
                    print("Verification button not found; submitting with Enter.")
                    await otp_input.press("Enter")

                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(2500)
                await page.goto(target_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                html = await page.content()
                assert_authenticated_html(page.url, html, "BallparkPal auth preflight")
                await save_ballparkpal_storage_state(context)
                print("BallparkPal login refreshed successfully.")
                return True
            finally:
                if keep_open:
                    print("Press Enter to close the browser...")
                    await asyncio.to_thread(input)
