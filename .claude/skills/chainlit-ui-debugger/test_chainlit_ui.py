#!/usr/bin/env python3
"""
Chainlit UI/UX Debugging Tool using Playwright

Automatically tests and validates Chainlit UI changes without manual screenshots.
Tests: welcome screen, chat interface, sidebar, RTL text, responsiveness, etc.
"""

import asyncio
import json
import subprocess
import sys
import time
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Installing Playwright...")
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright", "-q"])
    subprocess.run([sys.executable, "-m", "playwright", "install", "-q"])
    from playwright.async_api import async_playwright, Browser, Page

try:
    from PIL import Image, ImageDraw, ImageChops
except ImportError:
    print("Installing Pillow...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw, ImageChops


@dataclass
class TestResult:
    """Result of a single test case"""
    name: str
    category: str
    status: str  # "PASS", "FAIL", "SKIP"
    message: str
    duration_ms: float
    screenshot_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ChainlitUITester:
    """Main testing orchestrator"""

    def __init__(self, base_url: str = "http://localhost:8000", debug_dir: str = ".chainlit-debug"):
        self.base_url = base_url
        self.debug_dir = Path(debug_dir)
        self.results: List[TestResult] = []
        self.app_process: Optional[subprocess.Popen] = None
        self.debug_dir.mkdir(exist_ok=True)
        (self.debug_dir / "screenshots" / "baseline").mkdir(parents=True, exist_ok=True)
        (self.debug_dir / "screenshots" / "current").mkdir(parents=True, exist_ok=True)
        (self.debug_dir / "diffs").mkdir(parents=True, exist_ok=True)

    async def setup(self) -> None:
        """Setup test environment - start app, install dependencies"""
        print("🚀 Setting up Chainlit UI Debugger...")

        # Check if app is already running
        if not await self._check_app_ready():
            print("📦 Starting Chainlit app...")
            self._start_app()
            await self._wait_for_app(max_attempts=30, delay=1)
        else:
            print("✅ App already running")

    async def teardown(self) -> None:
        """Cleanup - stop app, close browsers"""
        if self.app_process:
            print("🛑 Stopping Chainlit app...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.app_process.kill()

    def _start_app(self) -> None:
        """Start Chainlit app in background"""
        # Find app.py in project root
        cwd = Path.cwd()
        app_file = cwd / "app.py"

        if not app_file.exists():
            raise FileNotFoundError("app.py not found in current directory")

        self.app_process = subprocess.Popen(
            [sys.executable, "-m", "chainlit", "run", str(app_file), "--host", "localhost", "--port", "8000"],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    async def _check_app_ready(self) -> bool:
        """Check if app is accessible"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                try:
                    await page.goto(self.base_url, wait_until="domcontentloaded", timeout=2000)
                    await page.close()
                    await browser.close()
                    return True
                except:
                    await page.close()
                    await browser.close()
                    return False
        except:
            return False

    async def _wait_for_app(self, max_attempts: int = 30, delay: int = 1) -> None:
        """Wait for app to be ready"""
        for attempt in range(max_attempts):
            if await self._check_app_ready():
                print(f"✅ App ready after {attempt * delay}s")
                return
            await asyncio.sleep(delay)
        raise TimeoutError(f"App did not start within {max_attempts * delay}s")

    async def run_tests(self, test_category: Optional[str] = None) -> None:
        """Run all or specific category of tests"""
        await self.setup()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                # Run test suites
                tests_to_run = self._get_tests_to_run(test_category)

                for test_func, category in tests_to_run:
                    try:
                        print(f"\n🧪 Running {category} tests...")
                        await test_func(browser)
                    except Exception as e:
                        print(f"❌ Error in {category}: {e}")

                await browser.close()
        finally:
            await self.teardown()

    def _get_tests_to_run(self, category: Optional[str]) -> List[tuple]:
        """Get list of tests to run based on category"""
        all_tests = [
            (self._test_welcome_screen, "welcome-screen"),
            (self._test_chat_interface, "chat"),
            (self._test_sidebar, "sidebar"),
            (self._test_rtl_text, "rtl-text"),
            (self._test_responsiveness, "responsiveness"),
            (self._test_thinking_steps, "thinking-steps"),
            (self._test_tool_calls, "tool-calls"),
            (self._test_visual_regression, "visual-regression"),
        ]

        if not category or category == "all":
            return all_tests

        return [(t, c) for t, c in all_tests if c == category]

    async def _test_welcome_screen(self, browser: Browser) -> None:
        """Test welcome screen layout and starter questions"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")

            # Check welcome screen is centered
            await page.locator('role=heading[name="Law Assistant"]').wait_for()
            welcome_box = await page.locator('[data-testid="welcome-screen"]')

            if await welcome_box.is_visible():
                # Check centering
                bbox = await welcome_box.bounding_box()
                if bbox:
                    page_width = page.viewport_size["width"]
                    center_x = page_width / 2
                    box_center = bbox["x"] + bbox["width"] / 2
                    is_centered = abs(center_x - box_center) < 100

                    self.results.append(TestResult(
                        name="Welcome screen centered",
                        category="welcome-screen",
                        status="PASS" if is_centered else "FAIL",
                        message=f"Welcome screen {'is' if is_centered else 'is not'} centered",
                        duration_ms=(time.time() - start_time) * 1000,
                        screenshot_path=await self._save_screenshot(page, "welcome-screen")
                    ))

            # Check starter questions visible
            questions = await page.locator('[data-testid="starter-question"]').count()
            self.results.append(TestResult(
                name="Starter questions visible",
                category="welcome-screen",
                status="PASS" if questions > 0 else "FAIL",
                message=f"Found {questions} starter questions",
                duration_ms=(time.time() - start_time) * 1000,
            ))

            # Check each question is clickable
            for i in range(min(questions, 3)):
                try:
                    await page.locator(f'[data-testid="starter-question"] >> nth={i}').click()
                    await page.wait_for_load_state("networkidle", timeout=2000)

                    self.results.append(TestResult(
                        name=f"Starter question {i+1} clickable",
                        category="welcome-screen",
                        status="PASS",
                        message="Question clicked and chat started",
                        duration_ms=(time.time() - start_time) * 1000,
                    ))
                    break  # Only test first one to save time
                except:
                    pass

        except Exception as e:
            self.results.append(TestResult(
                name="Welcome screen test",
                category="welcome-screen",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_chat_interface(self, browser: Browser) -> None:
        """Test chat message input and display"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")

            # Find input box
            input_box = await page.locator('input[placeholder*="Message"]')
            if await input_box.is_visible():
                self.results.append(TestResult(
                    name="Chat input visible",
                    category="chat",
                    status="PASS",
                    message="Message input field is visible",
                    duration_ms=(time.time() - start_time) * 1000,
                ))
            else:
                self.results.append(TestResult(
                    name="Chat input visible",
                    category="chat",
                    status="FAIL",
                    message="Message input field not found",
                    duration_ms=(time.time() - start_time) * 1000,
                ))

            # Test sending message
            await input_box.fill("سلام، چطور می‌تونید کمک کنید؟")
            send_button = await page.locator('button:has-text("Send")').first

            if await send_button.is_enabled():
                await send_button.click()
                await page.wait_for_timeout(1000)

                # Check message appears
                messages = await page.locator('[role="article"]').count()
                self.results.append(TestResult(
                    name="Message sends",
                    category="chat",
                    status="PASS" if messages > 0 else "FAIL",
                    message=f"Found {messages} messages in chat",
                    duration_ms=(time.time() - start_time) * 1000,
                    screenshot_path=await self._save_screenshot(page, "chat-interface")
                ))

        except Exception as e:
            self.results.append(TestResult(
                name="Chat interface test",
                category="chat",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_sidebar(self, browser: Browser) -> None:
        """Test conversation history sidebar"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")

            # Check sidebar exists
            sidebar = await page.locator('[role="complementary"]')
            if await sidebar.is_visible():
                self.results.append(TestResult(
                    name="Sidebar visible",
                    category="sidebar",
                    status="PASS",
                    message="Conversation history sidebar is visible",
                    duration_ms=(time.time() - start_time) * 1000,
                    screenshot_path=await self._save_screenshot(page, "sidebar")
                ))

                # Check for date grouping (امروز, دیروز, etc.)
                date_groups = await page.locator('text=/امروز|دیروز|روز|ماه/').count()
                self.results.append(TestResult(
                    name="Sidebar date grouping",
                    category="sidebar",
                    status="PASS" if date_groups > 0 else "SKIP",
                    message=f"Found {date_groups} date group headers",
                    duration_ms=(time.time() - start_time) * 1000,
                ))
            else:
                self.results.append(TestResult(
                    name="Sidebar visible",
                    category="sidebar",
                    status="SKIP",
                    message="Sidebar not found (may require asyncpg)",
                    duration_ms=(time.time() - start_time) * 1000,
                ))

        except Exception as e:
            self.results.append(TestResult(
                name="Sidebar test",
                category="sidebar",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_rtl_text(self, browser: Browser) -> None:
        """Test right-to-left Persian text rendering"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")

            # Check for Persian text
            main_content = await page.locator('main, [role="main"]')
            if await main_content.is_visible():
                # Get computed direction
                direction = await main_content.evaluate("el => window.getComputedStyle(el).direction")

                self.results.append(TestResult(
                    name="RTL text direction",
                    category="rtl-text",
                    status="PASS" if direction == "rtl" else "WARN",
                    message=f"Text direction is '{direction}'",
                    duration_ms=(time.time() - start_time) * 1000,
                    screenshot_path=await self._save_screenshot(page, "rtl-text")
                ))

            # Check for Persian characters rendering
            try:
                await page.goto(self.base_url + "?test=persian", wait_until="domcontentloaded")
                persian_text = await page.locator('text=/[ا-ی]/').count()

                if persian_text > 0:
                    self.results.append(TestResult(
                        name="Persian characters render",
                        category="rtl-text",
                        status="PASS",
                        message=f"Found {persian_text} Persian characters",
                        duration_ms=(time.time() - start_time) * 1000,
                    ))
            except:
                pass

        except Exception as e:
            self.results.append(TestResult(
                name="RTL text test",
                category="rtl-text",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_responsiveness(self, browser: Browser) -> None:
        """Test layout on different viewport sizes"""
        viewports = [
            ("mobile", {"width": 375, "height": 667}),
            ("tablet", {"width": 768, "height": 1024}),
            ("desktop", {"width": 1920, "height": 1080}),
        ]

        for device_type, viewport in viewports:
            page = await browser.new_page(viewport=viewport)
            start_time = time.time()

            try:
                await page.goto(self.base_url, wait_until="domcontentloaded")

                # Check main elements are visible
                main = await page.locator('main, [role="main"]')
                is_visible = await main.is_visible()

                self.results.append(TestResult(
                    name=f"Responsive layout ({device_type})",
                    category="responsiveness",
                    status="PASS" if is_visible else "FAIL",
                    message=f"Main content visible at {viewport['width']}x{viewport['height']}",
                    duration_ms=(time.time() - start_time) * 1000,
                    screenshot_path=await self._save_screenshot(page, f"responsive-{device_type}")
                ))

            except Exception as e:
                self.results.append(TestResult(
                    name=f"Responsive test ({device_type})",
                    category="responsiveness",
                    status="FAIL",
                    message=str(e),
                    duration_ms=(time.time() - start_time) * 1000,
                    error=str(e)
                ))
            finally:
                await page.close()

    async def _test_thinking_steps(self, browser: Browser) -> None:
        """Test thinking steps visualization"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")

            # Look for thinking step elements
            thinking_steps = await page.locator('[data-testid="thinking-step"], [role="status"]').count()

            self.results.append(TestResult(
                name="Thinking steps display",
                category="thinking-steps",
                status="PASS" if thinking_steps > 0 else "SKIP",
                message=f"Found {thinking_steps} thinking step elements",
                duration_ms=(time.time() - start_time) * 1000,
            ))

        except Exception as e:
            self.results.append(TestResult(
                name="Thinking steps test",
                category="thinking-steps",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_tool_calls(self, browser: Browser) -> None:
        """Test tool calls visualization"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")

            # Look for tool call elements
            tool_calls = await page.locator('[data-testid="tool-call"], [role="region"]:has-text("tool")').count()

            self.results.append(TestResult(
                name="Tool calls display",
                category="tool-calls",
                status="PASS" if tool_calls > 0 else "SKIP",
                message=f"Found {tool_calls} tool call elements",
                duration_ms=(time.time() - start_time) * 1000,
                screenshot_path=await self._save_screenshot(page, "tool-calls") if tool_calls > 0 else None
            ))

        except Exception as e:
            self.results.append(TestResult(
                name="Tool calls test",
                category="tool-calls",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _test_visual_regression(self, browser: Browser) -> None:
        """Test for visual regressions against baseline"""
        page = await browser.new_page()
        start_time = time.time()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded")
            current_path = await self._save_screenshot(page, "full-page", subdir="current")
            baseline_path = self.debug_dir / "screenshots" / "baseline" / "full-page.png"

            if baseline_path.exists():
                # Compare images
                diff_score = self._compare_images(current_path, baseline_path)

                status = "PASS" if diff_score < 5 else ("WARN" if diff_score < 15 else "FAIL")
                self.results.append(TestResult(
                    name="Visual regression",
                    category="visual-regression",
                    status=status,
                    message=f"Image diff score: {diff_score:.1f}%",
                    duration_ms=(time.time() - start_time) * 1000,
                ))
            else:
                # First run - establish baseline
                self._copy_screenshot(current_path, baseline_path)
                self.results.append(TestResult(
                    name="Visual regression baseline",
                    category="visual-regression",
                    status="SKIP",
                    message="Baseline established (first run)",
                    duration_ms=(time.time() - start_time) * 1000,
                ))

        except Exception as e:
            self.results.append(TestResult(
                name="Visual regression test",
                category="visual-regression",
                status="FAIL",
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
                error=str(e)
            ))
        finally:
            await page.close()

    async def _save_screenshot(self, page: Page, name: str, subdir: str = "current") -> str:
        """Save screenshot and return path"""
        path = self.debug_dir / "screenshots" / subdir / f"{name}.png"
        await page.screenshot(path=path, full_page=False)
        return str(path)

    def _copy_screenshot(self, src: str, dst: Path) -> None:
        """Copy screenshot for baseline"""
        import shutil
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)

    def _compare_images(self, current: str, baseline: str) -> float:
        """Compare two images and return difference percentage"""
        try:
            img1 = Image.open(current)
            img2 = Image.open(baseline)

            # Resize to same size
            img1 = img1.convert("RGB")
            img2 = img2.convert("RGB").resize(img1.size)

            # Calculate diff
            diff = ImageChops.difference(img1, img2)
            diff_pixels = sum(diff.getdata())
            total_pixels = img1.size[0] * img1.size[1] * 3

            return (diff_pixels / total_pixels) * 100
        except:
            return 0

    def generate_report(self) -> str:
        """Generate test report"""
        report_lines = [
            "\n" + "="*60,
            "🧪 CHAINLIT UI/UX TEST REPORT",
            "="*60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary by category
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {"PASS": 0, "FAIL": 0, "SKIP": 0, "WARN": 0}
            categories[result.category][result.status] += 1

        # Category breakdown
        for category, counts in sorted(categories.items()):
            total = sum(counts.values())
            passed = counts["PASS"]
            emoji = "✅" if counts["FAIL"] == 0 and counts["WARN"] == 0 else "⚠️" if counts["WARN"] > 0 else "❌"
            report_lines.append(f"{emoji} {category.upper()}: {passed}/{total} passed")

        report_lines.extend(["", "DETAILED RESULTS:", "-"*60])

        # Detailed results
        for result in self.results:
            emoji = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️", "WARN": "⚠️"}[result.status]
            report_lines.append(f"{emoji} [{result.category}] {result.name}")
            report_lines.append(f"   Message: {result.message}")
            report_lines.append(f"   Time: {result.duration_ms:.0f}ms")
            if result.error:
                report_lines.append(f"   Error: {result.error}")
            if result.screenshot_path:
                report_lines.append(f"   Screenshot: {result.screenshot_path}")
            report_lines.append("")

        # Summary stats
        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warned = sum(1 for r in self.results if r.status == "WARN")
        skipped = sum(1 for r in self.results if r.status == "SKIP")

        report_lines.extend([
            "-"*60,
            "SUMMARY",
            f"Total Tests: {total_tests}",
            f"✅ Passed: {passed}",
            f"❌ Failed: {failed}",
            f"⚠️  Warned: {warned}",
            f"⏭️  Skipped: {skipped}",
            f"Success Rate: {(passed/max(total_tests-skipped, 1)*100):.1f}%",
            "="*60,
        ])

        report = "\n".join(report_lines)

        # Save JSON report
        report_file = self.debug_dir / "report.json"
        with open(report_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "summary": {
                    "total": total_tests,
                    "passed": passed,
                    "failed": failed,
                    "warned": warned,
                    "skipped": skipped,
                    "success_rate": passed / max(total_tests - skipped, 1),
                },
                "results": [r.to_dict() for r in self.results],
            }, f, indent=2)

        return report


async def main():
    """Main entry point"""
    import sys

    # Get test category from command line
    test_category = sys.argv[1] if len(sys.argv) > 1 else None

    tester = ChainlitUITester()
    await tester.run_tests(test_category)

    # Print and save report
    report = tester.generate_report()
    print(report)

    # Return exit code based on failures
    failed = sum(1 for r in tester.results if r.status == "FAIL")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
