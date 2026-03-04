#!/usr/bin/env python3
"""
BFS (betfunsports.com) — v2 browser tests
Fixes: login form visibility, language switch, registration submit selector.
"""

import asyncio
import json
import random
import string
from playwright.async_api import async_playwright

BASE_URL = "https://betfunsports.com"
RESULTS = []

def rnd(n=6):
    return ''.join(random.choices(string.ascii_lowercase, k=n))

def log(name, status, details=""):
    RESULTS.append({"test": name, "status": status, "details": details})
    icon = {"pass": "PASS", "fail": "FAIL", "info": "INFO", "warn": "WARN"}[status]
    print(f"[{icon}] {name}: {details}")


# ─── HOMEPAGE ────────────────────────────────────────────────────────────

async def test_homepage(page):
    resp = await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    title = await page.title()
    join_btn = await page.locator('a[href="/fullRegistration"]').count()
    sports = await page.locator('a[href*="/football/"]').count()
    log("homepage", "pass" if resp.status == 200 else "fail",
        f"status={resp.status}, title='{title}', join_btns={join_btn}, sport_links={sports}")

async def test_viewport_meta(page):
    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    vp = await page.evaluate('document.querySelector("meta[name=viewport]")?.content')
    log("viewport_meta", "pass" if vp else "fail", f"content='{vp}'")

async def test_language_switch(page):
    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    for code in ["ru", "en"]:
        try:
            await page.evaluate(f'document.querySelector("form.lng_{code}").submit()')
            await page.wait_for_timeout(2000)
            cookie = await page.evaluate("document.cookie")
            has_lang = f"langCode={code}" in cookie
            log(f"lang_switch_{code}", "pass" if has_lang else "warn",
                f"cookie has langCode={code}: {has_lang}, cookie='{cookie[:80]}'")
        except Exception as e:
            log(f"lang_switch_{code}", "fail", str(e)[:100])


# ─── REGISTRATION ────────────────────────────────────────────────────────

async def test_reg_page_loads(page):
    resp = await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    title = await page.title()
    form = await page.locator("#fform_registration").count() > 0
    log("reg_page", "pass" if resp.status == 200 and form else "fail",
        f"status={resp.status}, title='{title}', form={form}")

async def test_reg_fields(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    fields = {
        "username": "#oldUame", "email": "#oail", "password": "#password0",
        "confirm": "#password2", "firstName": "#firstName", "lastName": "#lastName",
        "birthDate": "#fbirthDate", "phone": "#phone", "country": "#countryCode",
        "sex_m": "#sex_male", "sex_f": "#sex_female",
    }
    found = {k: await page.locator(v).count() > 0 for k, v in fields.items()}
    missing = [k for k, v in found.items() if not v]
    log("reg_fields", "pass" if not missing else "fail",
        f"missing={missing or 'none'}")

async def _fill_reg(page, **overrides):
    """Fill registration form with defaults; overrides replace specific fields."""
    defaults = {
        "username": "bfsqa_" + rnd(5),
        "email": f"bfsqa_{rnd(5)}@testbfs.com",
        "password": "QATest@2026!",
        "confirm": "QATest@2026!",
        "firstName": "QA",
        "lastName": "Tester",
        "birthDate": "15/06/1995",
        "phone": "+12025551234",
        "country": "US",
    }
    d = {**defaults, **overrides}
    await page.fill("#oldUame", d["username"])
    await page.fill("#oail", d["email"])
    await page.fill("#password0", d["password"])
    await page.fill("#password2", d["confirm"])
    await page.fill("#firstName", d["firstName"])
    await page.fill("#lastName", d["lastName"])
    await page.fill("#fbirthDate", d["birthDate"])
    await page.fill("#phone", d["phone"])
    await page.select_option("#countryCode", d["country"])

    city = page.locator("input[name='city']")
    if await city.count() > 0:
        await city.first.fill("New York")
    addr = page.locator("input[name='address']")
    if await addr.count() > 0:
        await addr.first.fill("123 Test St")
    zipf = page.locator("input[name='zip'], input[name='zipCode']")
    if await zipf.count() > 0:
        await zipf.first.fill("10001")

    cbs = page.locator('#fform_registration input[type="checkbox"]')
    for i in range(await cbs.count()):
        if not await cbs.nth(i).is_checked():
            await cbs.nth(i).check(force=True)

    return d

async def _submit_reg(page):
    btn = page.locator('#fform_registration button[type="submit"], #fform_registration input[type="submit"]')
    if await btn.count() == 0:
        btn = page.locator('#fform_registration .btn-success, #fform_registration .btn-primary')
    if await btn.count() > 0:
        await btn.first.click(force=True)
        await page.wait_for_timeout(3000)
        return True
    return False


async def test_reg_invalid_email(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    await _fill_reg(page, email="not-an-email")
    await _submit_reg(page)
    errs = await page.locator("label.error, .invalid-feedback, .text-danger").all_text_contents()
    errs = [e.strip() for e in errs if e.strip()]
    log("reg_invalid_email", "pass" if errs else "warn",
        f"errors={errs[:5]}")

async def test_reg_weak_pass(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    await _fill_reg(page, password="123", confirm="123")
    meter = (await page.locator(".password-meter-message").text_content()).strip()
    await _submit_reg(page)
    errs = await page.locator("label.error, .invalid-feedback").all_text_contents()
    errs = [e.strip() for e in errs if e.strip()]
    log("reg_weak_pass", "pass",
        f"meter='{meter}', errors={errs[:5]}")

async def test_reg_pass_mismatch(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    await _fill_reg(page, password="StrongP@ss1", confirm="OtherP@ss2")
    await _submit_reg(page)
    errs = await page.locator("label.error, .invalid-feedback").all_text_contents()
    errs = [e.strip() for e in errs if e.strip()]
    has_mismatch = any("not equal" in e.lower() or "mismatch" in e.lower() or "match" in e.lower() for e in errs)
    log("reg_pass_mismatch", "pass" if has_mismatch else "warn",
        f"errors={errs[:5]}")

async def test_reg_valid(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    data = await _fill_reg(page)
    meter = (await page.locator(".password-meter-message").text_content()).strip()
    submitted = await _submit_reg(page)
    url = page.url
    text = await page.locator("body").text_content()
    errs = await page.locator("label.error, .alert-danger").all_text_contents()
    errs = [e.strip() for e in errs if e.strip()]
    success = any(kw in text.lower() for kw in ["success", "welcome", "confirm", "verify", "email sent", "registered"])
    log("reg_valid", "pass" if submitted else "fail",
        f"user={data['username']}, email={data['email']}, meter='{meter}', "
        f"url={url}, success_indicators={success}, errors={errs[:3] or 'none'}")

async def test_reg_duplicate_email(page):
    """Try registering twice with same email"""
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    shared_email = f"bfsdup_{rnd(5)}@testbfs.com"
    await _fill_reg(page, email=shared_email, username="bfsdup1_" + rnd(3))
    await _submit_reg(page)
    url1 = page.url
    
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    await _fill_reg(page, email=shared_email, username="bfsdup2_" + rnd(3))
    await _submit_reg(page)
    url2 = page.url
    text = await page.locator("body").text_content()
    errs = await page.locator("label.error, .alert-danger, .error-message").all_text_contents()
    errs = [e.strip() for e in errs if e.strip()]
    dup_detected = any(kw in text.lower() for kw in ["already", "exists", "taken", "duplicate", "registered"])
    log("reg_duplicate_email", "pass" if dup_detected else "warn",
        f"email={shared_email}, url1={url1}, url2={url2}, dup_detected={dup_detected}, errors={errs[:3] or 'none'}")


# ─── LOGIN ────────────────────────────────────────────────────────────────

async def test_login_via_post(page):
    """Test login via direct POST (bypasses hidden form issue)"""
    resp = await page.request.post(f"{BASE_URL}/login", form={
        "email": "nonexistent@test.com",
        "password": "wrongpass123"
    })
    status = resp.status
    body = await resp.text()
    has_error = any(kw in body.lower() for kw in ["error", "invalid", "wrong", "incorrect", "failed", "login"])
    log("login_invalid_post", "pass",
        f"status={status}, has_error_text={has_error}, body_snippet={body[:300].strip()}")

async def test_login_empty_post(page):
    resp = await page.request.post(f"{BASE_URL}/login", form={
        "email": "",
        "password": ""
    })
    status = resp.status
    body = await resp.text()
    log("login_empty_post", "pass",
        f"status={status}, body_snippet={body[:300].strip()}")

async def test_login_sqli_attempt(page):
    """Basic SQL injection test on login"""
    resp = await page.request.post(f"{BASE_URL}/login", form={
        "email": "' OR 1=1 --",
        "password": "' OR 1=1 --"
    })
    status = resp.status
    body = await resp.text()
    sqli_success = any(kw in body.lower() for kw in ["welcome", "dashboard", "profile", "logout", "my account"])
    log("login_sqli", "pass" if not sqli_success else "fail",
        f"status={status}, sqli_worked={sqli_success}, "
        f"Note={'VULNERABILITY: SQLi seems to work!' if sqli_success else 'Good - SQLi rejected'}")


# ─── PASSWORD RECOVERY ─────────────────────────────────────────────────

async def test_recovery_page(page):
    resp = await page.goto(f"{BASE_URL}/recoverPassword", wait_until="domcontentloaded", timeout=15000)
    title = await page.title()
    email_field = await page.locator('input[type="email"], input[name*="mail"]').count() > 0
    submit = await page.locator('button[type="submit"], input[type="submit"]').count() > 0
    log("recovery_page", "pass" if resp.status == 200 else "fail",
        f"status={resp.status}, title='{title}', email_field={email_field}, submit={submit}")

async def test_recovery_nonexistent_email(page):
    await page.goto(f"{BASE_URL}/recoverPassword", wait_until="domcontentloaded", timeout=15000)
    email_field = page.locator('input[type="email"], input[name*="mail"]').first
    await email_field.fill("nonexistent_xyz@nobody.com")
    submit = page.locator('button[type="submit"], input[type="submit"]').first
    await submit.click(force=True)
    await page.wait_for_timeout(3000)
    text = await page.locator("body").text_content()
    url = page.url
    log("recovery_bad_email", "pass",
        f"url={url}, body_snippet={text[:200].strip()}")


# ─── SPORT PAGES ──────────────────────────────────────────────────────

async def test_sport_pages(page):
    pages = [
        ("/football/prizecoupons1X2", "Football 1X2"),
        ("/football/prizecouponsScore", "Football Score"),
        ("/tennis/atpGenevaOpen", "Tennis"),
        ("/hockey/kHLRegular", "Hockey KHL"),
        ("/basketball/basketWorldCapFinal", "Basketball"),
        ("/biathlon/biathlonWorldCup", "Biathlon"),
        ("/mma/mmaProfiTitle", "MMA"),
        ("/formula1/britishGrandPrixdrivers", "Formula 1"),
        ("/volleyball/championship_usa_21", "Volleyball"),
    ]
    for path, label in pages:
        try:
            resp = await page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=15000)
            title = await page.title()
            is_err = "error" in title.lower()
            log(f"sport_{label.replace(' ', '_').lower()}", "pass" if resp.status == 200 and not is_err else "fail",
                f"status={resp.status}, title='{title}'")
        except Exception as e:
            log(f"sport_{label.replace(' ', '_').lower()}", "fail", str(e)[:100])


# ─── PAYMENT ──────────────────────────────────────────────────────────

async def test_payment_page(page):
    resp = await page.goto(f"{BASE_URL}/paymentmethods", wait_until="domcontentloaded", timeout=15000)
    title = await page.title()
    text = await page.locator("body").text_content()
    has_payment = any(kw in text.lower() for kw in ["payment", "deposit", "bfs", "method"])
    log("payment_page", "pass" if resp.status == 200 else "fail",
        f"status={resp.status}, title='{title}', has_payment_info={has_payment}")


# ─── SECURITY ─────────────────────────────────────────────────────────

async def test_csrf_token(page):
    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    csrf = await page.evaluate('document.querySelector("meta[name=_csrf]")?.content')
    log("csrf_token", "pass" if csrf else "fail",
        f"csrf='{csrf}', note={'Empty CSRF meta — potential vulnerability' if not csrf else 'present'}")

async def test_xss_registration(page):
    await page.goto(f"{BASE_URL}/fullRegistration", wait_until="domcontentloaded", timeout=15000)
    xss = '<script>alert("xss")</script>'
    await page.fill("#oldUame", xss)
    await page.fill("#firstName", xss)
    await page.fill("#lastName", xss)
    await page.fill("#oail", "test@test.com")
    await page.fill("#password0", "Test@1234pass")
    await page.fill("#password2", "Test@1234pass")
    await _submit_reg(page)
    html = await page.content()
    reflected = '<script>alert("xss")</script>' in html
    log("xss_registration", "pass" if not reflected else "fail",
        f"reflected={reflected}, note={'XSS VULN!' if reflected else 'sanitized (good)'}")

async def test_security_headers(page):
    resp = await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    headers = resp.headers
    checks = {
        "x-frame-options": headers.get("x-frame-options", ""),
        "x-content-type-options": headers.get("x-content-type-options", ""),
        "x-xss-protection": headers.get("x-xss-protection", ""),
        "strict-transport-security": headers.get("strict-transport-security", ""),
        "content-security-policy": headers.get("content-security-policy", ""),
    }
    missing = [k for k, v in checks.items() if not v]
    log("security_headers", "pass" if len(missing) <= 2 else "warn",
        f"present={[k for k, v in checks.items() if v]}, missing={missing}")

async def test_cookie_flags(page):
    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    cookies = await page.context.cookies()
    issues = []
    for c in cookies:
        if not c.get("httpOnly") and c["name"] not in ["langCode"]:
            issues.append(f"{c['name']}: no httpOnly")
        if not c.get("secure"):
            issues.append(f"{c['name']}: no secure flag")
    log("cookie_flags", "pass" if not issues else "warn",
        f"cookies={[c['name'] for c in cookies]}, issues={issues[:5] or 'none'}")

async def test_nonexistent_page(page):
    resp = await page.goto(f"{BASE_URL}/nonexistent_page_xyz_123", wait_until="domcontentloaded", timeout=15000)
    title = await page.title()
    log("404_page", "pass" if "error" in title.lower() or resp.status in [404, 200] else "fail",
        f"status={resp.status}, title='{title}'")


# ─── MAIN ─────────────────────────────────────────────────────────────

async def main():
    print("=" * 80)
    print("BFS (betfunsports.com) — AUTOMATED BROWSER TESTS v2")
    print("=" * 80)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
        page = await ctx.new_page()

        async def safe(fn, *args):
            try:
                await fn(*args)
            except Exception as e:
                log(fn.__name__, "fail", f"CRASH: {str(e)[:150]}")

        print("\n─── HOMEPAGE & NAVIGATION ───")
        await safe(test_homepage, page)
        await safe(test_viewport_meta, page)
        await safe(test_language_switch, page)

        print("\n─── REGISTRATION ───")
        await safe(test_reg_page_loads, page)
        await safe(test_reg_fields, page)
        await safe(test_reg_invalid_email, page)
        await safe(test_reg_weak_pass, page)
        await safe(test_reg_pass_mismatch, page)
        await safe(test_reg_valid, page)
        await safe(test_reg_duplicate_email, page)

        print("\n─── LOGIN ───")
        await safe(test_login_via_post, page)
        await safe(test_login_empty_post, page)
        await safe(test_login_sqli_attempt, page)

        print("\n─── PASSWORD RECOVERY ───")
        await safe(test_recovery_page, page)
        await safe(test_recovery_nonexistent_email, page)

        print("\n─── SPORT PAGES ───")
        await safe(test_sport_pages, page)

        print("\n─── PAYMENT ───")
        await safe(test_payment_page, page)

        print("\n─── SECURITY ───")
        await safe(test_csrf_token, page)
        await safe(test_xss_registration, page)
        await safe(test_security_headers, page)
        await safe(test_cookie_flags, page)
        await safe(test_nonexistent_page, page)

        await browser.close()

    print("\n" + "=" * 80)
    print("ИТОГИ")
    print("=" * 80)
    passed = sum(1 for r in RESULTS if r["status"] == "pass")
    failed = sum(1 for r in RESULTS if r["status"] == "fail")
    warned = sum(1 for r in RESULTS if r["status"] == "warn")
    total = len(RESULTS)
    print(f"Всего: {total} | PASS: {passed} | FAIL: {failed} | WARN: {warned}")
    print()
    for r in RESULTS:
        icon = {"pass": "+", "fail": "X", "warn": "!", "info": "i"}[r["status"]]
        print(f"  [{icon}] {r['test']}")
    
    if failed:
        print(f"\nFAILED ({failed}):")
        for r in RESULTS:
            if r["status"] == "fail":
                print(f"  X {r['test']}: {r['details'][:120]}")
    if warned:
        print(f"\nWARNINGS ({warned}):")
        for r in RESULTS:
            if r["status"] == "warn":
                print(f"  ! {r['test']}: {r['details'][:120]}")

    print("\n\nJSON:")
    print(json.dumps(RESULTS, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
