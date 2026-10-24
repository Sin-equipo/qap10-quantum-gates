"""Browser regressions for motion, truthful comparison and playback completion.

Optional developer checks: pip install playwright && python -m playwright install chromium.
The fixture owns a separate local server; it never executes a new Qiskit job.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

playwright_api = pytest.importorskip("playwright.sync_api", reason="Install Playwright to run the optional browser regressions")
expect = playwright_api.expect
ROOT = Path(__file__).resolve().parents[1]
PORT = 8505
URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def visual_server(tmp_path_factory):
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", PORT)) == 0:
            pytest.fail(f"Port {PORT} is already in use; the tests will not take over another server")
    log = (tmp_path_factory.mktemp("visual-server") / "streamlit.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app/app.py", "--server.headless=true",
         "--server.address=127.0.0.1", f"--server.port={PORT}", "--server.fileWatcherType=none"],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail("The owned Streamlit test server stopped during startup")
            try:
                urllib.request.urlopen(URL + "/_stcore/health", timeout=1).close()
                break
            except (OSError, TimeoutError):
                time.sleep(0.1)
        else:
            pytest.fail("The owned Streamlit test server did not become ready")
        yield URL
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=15, check=False)
        else:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()


@pytest.fixture(scope="module")
def browser(visual_server):
    with playwright_api.sync_playwright() as p:
        try:
            result = p.chromium.launch(headless=True)
        except playwright_api.Error as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip("Run python -m playwright install chromium to install the browser")
            raise
        yield result
        result.close()


@pytest.fixture
def page(browser, visual_server, tmp_path, request):
    context = browser.new_context(viewport={"width": 1366, "height": 768})
    result = context.new_page()
    errors = []
    result.on("pageerror", lambda exc: errors.append(str(exc)))
    result.add_init_script("""
      window.__walkClears = 0;
      const original = CanvasRenderingContext2D.prototype.clearRect;
      CanvasRenderingContext2D.prototype.clearRect = function(...args) {
        window.__walkClears += 1;
        return original.apply(this, args);
      };
    """)
    result.goto(visual_server, wait_until="networkidle")
    result.locator("#lab").wait_for(timeout=30000)
    expect(result.locator("#lab")).to_have_attribute("data-phase", "ready")
    yield result
    result.screenshot(path=str(tmp_path / f"{request.node.name}.png"))
    context.close()
    assert not errors, errors


def set_n(page, n):
    page.locator("#size").evaluate(
        "(el, n) => {el.value=String(n);el.dispatchEvent(new Event('input',{bubbles:true}));}", n)
    expect(page.locator("#n-label")).to_have_text(str(n))


def dataset(page, element, key):
    return float(page.locator(element).evaluate("(el,key)=>el.dataset[key]", key))


def walk(page, *, view="all", compare=None, speed="4"):
    page.locator("#walk").click()
    if compare is not None:
        page.locator("#walk-compare").select_option(compare)
    page.locator("#walk-view").select_option(view)
    page.locator("#speed").select_option(speed)


def finish(page, timeout=12000):
    expect(page.locator("#lab")).to_have_attribute("data-phase", "done", timeout=timeout)
    expect(page.locator("#lab")).to_have_attribute("data-playing", "false")
    for side in ("left", "right"):
        assert dataset(page, "#arrivals-" + side, "arrived") == dataset(page, "#arrivals-" + side, "total")
        assert dataset(page, "#walked-" + side, "travelled") == pytest.approx(
            dataset(page, "#walked-" + side, "target"))


def test_n1_has_no_passengers_or_empty_wait(page):
    set_n(page, 1)
    page.locator("#walk").click()
    finish(page, timeout=1000)
    assert dataset(page, "#arrivals-left", "total") == 0


def test_n2_stops_at_the_actual_last_arrival(page):
    set_n(page, 2)
    started = time.monotonic()
    walk(page, speed="1")
    finish(page, timeout=3000)
    assert time.monotonic() - started < 4  # old fixed window was eight seconds


def test_default_impact_compares_the_same_demand_before_and_after(page):
    walk(page, view="group")
    expect(page.locator("#cost-left")).to_have_text("536")
    expect(page.locator("#cost-right")).to_have_text("374")
    assert dataset(page, "#arrivals-left", "total") == dataset(page, "#arrivals-right", "total")
    assert dataset(page, "#walked-left", "target") > dataset(page, "#walked-right", "target")


@pytest.mark.parametrize("n", [3, 4, 6, 10])
def test_all_flows_finish_at_the_displayed_qap_cost(page, n):
    set_n(page, n)
    walk(page, view="all")
    finish(page)
    for side in ("left", "right"):
        assert dataset(page, "#walked-" + side, "target") == float(page.locator("#cost-" + side).inner_text())


def test_equal_algorithm_assignments_keep_identical_motion(page):
    walk(page, view="all", compare="algorithms", speed="1")
    page.wait_for_timeout(250)
    page.locator("#play").click()
    expect(page.locator("#lab")).to_have_attribute("data-playing", "false")
    assert dataset(page, "#walked-left", "target") == dataset(page, "#walked-right", "target") == 374
    assert dataset(page, "#walked-left", "travelled") == pytest.approx(dataset(page, "#walked-right", "travelled"))
    assert dataset(page, "#arrivals-left", "arrived") == dataset(page, "#arrivals-right", "arrived")


def test_group_view_reduces_figures_without_changing_total_cost(page):
    walk(page, view="group", speed="1")
    group_count = dataset(page, "#arrivals-left", "total")
    global_cost = page.locator("#cost-left").inner_text()
    page.locator("#walk-view").select_option("all")
    assert 0 < group_count < dataset(page, "#arrivals-left", "total") == 114
    assert page.locator("#cost-left").inner_text() == global_cost


def test_pause_freezes_motion_and_stops_canvas_work(page):
    walk(page, speed="1")
    page.wait_for_timeout(200)
    page.locator("#play").click()
    expect(page.locator("#lab")).to_have_attribute("data-playing", "false")
    page.wait_for_timeout(150)
    value = dataset(page, "#walked-left", "travelled")
    clears = page.evaluate("window.__walkClears")
    page.wait_for_timeout(300)
    assert dataset(page, "#walked-left", "travelled") == value
    assert page.evaluate("window.__walkClears") - clears <= 2


def test_visual_speed_changes_duration_and_completion_is_quiescent(page):
    start = time.monotonic()
    walk(page, view="group", speed="1")
    finish(page)
    normal = time.monotonic() - start
    start = time.monotonic()
    walk(page, view="group", speed="4")
    finish(page)
    accelerated = time.monotonic() - start
    assert accelerated < normal * 0.7
    page.wait_for_timeout(150)
    clears = page.evaluate("window.__walkClears")
    page.wait_for_timeout(300)
    assert page.evaluate("window.__walkClears") - clears <= 2


def test_tour_stops_after_its_last_connection(page):
    walk(page, view="tour", speed="4")
    finish(page, timeout=15000)
    expect(page.locator("#play")).to_contain_text("Repetir")


def test_optimum_reference_and_new_size_reset_are_explicit(page):
    walk(page, compare="optimum")
    expect(page.locator("#cost-left")).to_have_text("340")
    set_n(page, 4)
    expect(page.locator("#lab")).to_have_attribute("data-phase", "ready")
    expect(page.locator("#lab")).to_have_attribute("data-playing", "false")
    assert page.locator("#gates-left [data-gate]").count() == 4


def test_recorded_sampling_finishes_instead_of_automatically_walking(page):
    page.locator('[data-size="4"]').click()
    page.locator("#samples").click()
    page.locator("#speed").select_option("4")
    expect(page.locator("#lab")).to_have_attribute("data-phase", "sampledone", timeout=6000)
    expect(page.locator("#lab")).to_have_attribute("data-playing", "false")
    expect(page.locator("#clock-label")).to_contain_text("256")


@pytest.mark.parametrize("width,height", [(1366, 768), (1920, 1080)])
def test_desktop_layout_keeps_controls_and_readouts_inside_the_screen(page, width, height):
    page.set_viewport_size({"width": width, "height": height})
    walk(page)
    assert page.evaluate("document.documentElement.scrollHeight") <= height
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    root = page.locator("#lab").bounding_box()
    for name in ("#walk-view", "#walk-compare", "#walked-left", "#walked-right", "#play", "#timeline"):
        box = page.locator(name).bounding_box()
        assert box and box["x"] >= root["x"] - 1
        assert box["x"] + box["width"] <= root["x"] + root["width"] + 1
        assert box["y"] + box["height"] <= height


def test_every_benchmark_size_has_the_corresponding_number_of_gates(page):
    for n in range(1, 11):
        set_n(page, n)
        assert page.locator("#gates-left [data-gate]").count() == n
        assert page.locator("#gates-right [data-gate]").count() == n
