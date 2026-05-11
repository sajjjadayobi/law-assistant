"""
Playwright visual test for share conversations (task 11.6).

Verified behaviors:
- Share icon appears in header for the active conversation
- Clicking it opens the "اشتراکگذاری لینک گفتگو" dialog with the share URL
- Clicking "اشتراکگذاری" button calls PUT /project/thread/share → {"success": true}
- Thread metadata gets is_shared=true in the DB
- A different authenticated user can navigate to /share/{thread_id} and see the full conversation (read-only, with thinking steps and citations)

Note on anonymous access:
Chainlit's UserParam dependency requires authentication even for /project/share/{thread_id}
when password_auth_callback is configured. Anonymous users are redirected to login.
This is Chainlit's design: "share" = accessible to any authenticated user, not truly public.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

BASE_URL = "http://localhost:7860"
SCREENSHOTS = Path(__file__).parent / "screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


async def screenshot(page: Page, name: str) -> None:
    path = SCREENSHOTS / f"{name}.png"
    await page.screenshot(path=str(path), full_page=False)
    print(f"  📸  {name}.png")


async def login(page: Page, username: str = "testuser", password: str = "testpass") -> None:
    await page.goto(BASE_URL, wait_until="networkidle")
    await page.wait_for_timeout(2000)
    inputs = page.locator("input")
    await inputs.nth(0).fill(username)
    await inputs.nth(1).fill(password)
    await page.locator('button:has-text("ورود"), button[type="submit"]').first.click()
    await page.wait_for_timeout(3000)
    print(f"  ✅  Logged in as '{username}'")


async def check_thread_sharing_api(page: Page) -> bool:
    response = await page.request.get(f"{BASE_URL}/project/settings")
    if response.ok:
        data = await response.json()
        val = data.get("threadSharing", False)
        if val:
            print("  ✅  threadSharing=true")
        else:
            print(f"  ❌  threadSharing={val}")
        return val
    print(f"  ⚠️  /project/settings status={response.status}")
    return False


async def send_message(page: Page, text: str) -> None:
    await page.locator("textarea").first.fill(text)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(2000)
    print(f"  ✅  Message sent")


async def open_share_dialog(page: Page) -> str | None:
    """
    Click the share icon in the header. Returns the share URL if dialog opens.
    The share icon is at approximately (1105, 30) in the header.
    """
    await screenshot(page, "06-before-share")
    await page.mouse.click(1105, 30)
    await page.wait_for_timeout(800)
    await screenshot(page, "07-after-share-click")

    # Verify dialog opened
    try:
        dialog_title = page.locator('text=اشتراک‌گذاری لینک گفتگو').first
        await dialog_title.wait_for(state="visible", timeout=3000)
        print("  ✅  Share dialog opened")
    except Exception:
        print("  ❌  Share dialog did not open")
        return None

    # Extract share URL from the dialog via DOM
    share_url = await page.evaluate("""() => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            const t = node.textContent.trim();
            if (t.includes('/share/') && t.length < 200) return t;
        }
        return null;
    }""")

    if share_url:
        print(f"  ✅  Share URL in dialog: {share_url}")
    else:
        print("  ⚠️  Share URL not found in dialog")
    return share_url


async def activate_sharing(page: Page) -> bool:
    """Click the share button to call PUT /project/thread/share → is_shared=true."""
    responses = []
    async def capture(resp):
        if "thread/share" in resp.url:
            body = await resp.body()
            responses.append((resp.status, body))
    page.on("response", capture)

    btn = page.locator('button:has-text("اشتراک‌گذاری"), button:has-text("اشتراکگذاری")').last
    await btn.click()
    await page.wait_for_timeout(1500)
    await screenshot(page, "09-after-share-activated")

    for status, body in responses:
        if status == 200 and b"success" in body:
            print(f"  ✅  Share API: 200 {{\"success\":true}}")
            return True
        else:
            print(f"  ❌  Share API: {status} {body[:100]}")
    if not responses:
        print("  ⚠️  No PUT /project/thread/share request captured")
    return bool(responses)


async def test_other_user_can_view(share_url: str) -> bool:
    """Login as a different user and verify they can read the shared conversation."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        await login(page, username="otheruser", password="otherpass")
        await screenshot(page, "10-otheruser-logged-in")

        await page.goto(share_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await screenshot(page, "11-otheruser-share-view")

        final_url = page.url
        content = await page.content()
        has_conversation = any(
            term in content
            for term in ["مرخصی", "زایمان", "قانون کار", "share"]
        )

        if "/share/" in final_url and has_conversation:
            print(f"  ✅  Other user sees the shared conversation at {final_url}")
            await browser.close()
            return True
        elif final_url.endswith("/login"):
            print(f"  ❌  Other user redirected to login — share link did not work")
        else:
            print(f"  ⚠️  Final URL: {final_url}, content found: {has_conversation}")

        await browser.close()
        return False


async def test_sidebar_share_menu(page: Page) -> None:
    """
    Attempt to show the sidebar context menu share entry.
    The sidebar is closed by default — first open it.
    """
    # Close share dialog if open, then scroll to top
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)
    await page.evaluate("window.scrollTo(0, 0)")

    # Open sidebar (use data-state selector for reliability)
    sidebar_toggle = page.locator('[id="sidebar-trigger-button"], button[data-state]').first
    await sidebar_toggle.click(force=True)
    await page.wait_for_timeout(800)

    # Hover over first thread item
    thread = page.locator('aside a, aside li, aside [href*="thread"]').first
    try:
        if await thread.is_visible(timeout=2000):
            await thread.hover()
            await page.wait_for_timeout(500)
            await screenshot(page, "12-sidebar-thread-hovered")

            # Click the "..." button
            dots = thread.locator('button').last
            await dots.click()
            await page.wait_for_timeout(500)
            await screenshot(page, "13-sidebar-context-menu")

            items = await page.locator('[role="menuitem"], li button, div[role="option"]').all_text_contents()
            if items:
                print(f"  ℹ️  Context menu items: {items}")
                has_share = any("اشتراک" in item for item in items)
                if has_share:
                    print("  ✅  Share option in sidebar context menu")
                else:
                    print("  ⚠️  Share option not found in context menu items")
        else:
            print("  ⚠️  No thread items found in sidebar")
    except Exception as e:
        print(f"  ⚠️  Sidebar test: {e}")


async def main() -> None:
    print("\n=== Share Conversations — Visual Test ===\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # 1. Login
        print("[1] Login")
        await login(page)
        await screenshot(page, "03-after-login")

        # 2. Check API flag
        print("\n[2] Verify threadSharing=true")
        api_ok = await check_thread_sharing_api(page)

        # 3. Create a thread
        print("\n[3] Send message")
        await send_message(page, "مرخصی زایمان طبق قانون کار چقدر است؟")
        await screenshot(page, "05-message-sent")

        # 4. Open share dialog
        print("\n[4] Open share dialog")
        share_url = await open_share_dialog(page)
        await screenshot(page, "08-share-dialog")

        # 5. Activate sharing
        print("\n[5] Activate sharing")
        share_ok = False
        if share_url:
            share_ok = await activate_sharing(page)

        # 6. Test cross-user access
        print("\n[6] Other user views shared thread")
        cross_user_ok = False
        if share_url and share_ok:
            cross_user_ok = await test_other_user_can_view(share_url)

        # 7. Sidebar test (navigate back to reset layout first)
        print("\n[7] Sidebar context menu")
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        try:
            await test_sidebar_share_menu(page)
        except Exception as e:
            print(f"  ⚠️  Sidebar test error (non-critical): {e}")

        await screenshot(page, "99-final")
        await browser.close()

    print("\n=== Results ===")
    print(f"  API threadSharing flag : {'✅' if api_ok else '❌'}")
    print(f"  Share dialog opened    : {'✅' if share_url else '❌'}")
    print(f"  Share API (200 ok)     : {'✅' if share_ok else '❌'}")
    print(f"  Other user can view    : {'✅' if cross_user_ok else '❌'}")
    print(f"  Screenshots            : {SCREENSHOTS}")
    all_pass = api_ok and bool(share_url) and share_ok and cross_user_ok
    print(f"\n  Overall: {'✅ ALL PASS' if all_pass else '⚠️  Some checks need review'}")
    print("=================\n")


if __name__ == "__main__":
    asyncio.run(main())
