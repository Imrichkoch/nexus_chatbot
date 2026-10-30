"""Standalone RAG desktop/mobile checks against an isolated local test server."""
import os
import tempfile
from pathlib import Path
from threading import Thread

import uvicorn
from playwright.sync_api import sync_playwright, expect

from conftest import FakeAI, FakeModelCatalog, FakeLDAP
from ui_smoke_runner import wait_for_port
from nexus.app import create_app


def main():
    os.environ['NEXUS_RAG_ONLY'] = '1'
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        app = create_app(database_path=str(root / 'app.db'),
                         synthetic_database_path=str(root / 'demo.db'),
                         ai_provider=FakeAI(), model_catalog=FakeModelCatalog(),
                         ldap_authenticator=FakeLDAP(root / 'ldap'), secure_cookies=False)
        app.state.store.create_local_user(name='rag-admin', password='TestPassword!2026', role='admin')
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=8766, log_level='warning'))
        thread = Thread(target=server.run, daemon=True)
        thread.start()
        wait_for_port(8766)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for width in (1440, 390):
                    page = browser.new_page(viewport={'width': width, 'height': 900})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto('http://127.0.0.1:8766/')
                    page.wait_for_load_state('networkidle')
                    page.locator('#login-form input[name=identifier]').fill('rag-admin')
                    page.locator('#login-form input[name=password]').fill('TestPassword!2026')
                    page.locator('#login-form button[type=submit]').click()
                    expect(page.locator('body')).to_have_class(__import__('re').compile('rag-only'))
                    expect(page.locator('#agent-switcher')).to_be_hidden()
                    expect(page.locator('#empty-description')).to_contain_text('documents')
                    page.evaluate("document.querySelector('#admin-nav').click()")
                    expect(page.locator('#settings-model')).not_to_have_value('')
                    for selector in ('.admin-card--infra', '.admin-card--data', '.admin-card--ldap'):
                        expect(page.locator(selector)).to_be_hidden()
                    page.locator('#settings-model').fill('test/rag-model')
                    with page.expect_response('**/api/admin/settings') as result:
                        page.locator('#settings-form button[type=submit]').click()
                    assert result.value.status == 200
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    assert not errors, errors
                    page.close()
                browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=10)
    print('RAG-only UI passed: desktop/mobile, no other agents, admin settings save, no overflow or JS errors.')


if __name__ == '__main__':
    main()
