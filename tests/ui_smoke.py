from pathlib import Path

from playwright.sync_api import sync_playwright


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
OUTPUT_DIR.mkdir(exist_ok=True)


def run() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        console_errors: list[str] = []

        mobile_auth = browser.new_page(viewport={"width": 390, "height": 844})
        mobile_auth.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            and "status of 401" not in message.text
            else None,
        )
        mobile_auth.goto("http://127.0.0.1:8765/")
        mobile_auth.wait_for_load_state("networkidle")
        mobile_auth.locator("#auth-view").wait_for(state="visible")
        mobile_auth.locator('[data-auth-mode="register"]').click()
        mobile_auth.locator("#register-form").wait_for(state="visible")
        assert (
            mobile_auth.locator('[data-auth-mode="register"]').get_attribute(
                "aria-selected"
            )
            == "true"
        )
        mobile_auth.locator('[data-auth-mode="login"]').click()
        mobile_auth.locator("#login-form").wait_for(state="visible")
        mobile_auth.screenshot(
            path=str(OUTPUT_DIR / "nexus-auth-mobile.png"),
            full_page=True,
        )
        mobile_auth.close()

        desktop = browser.new_page(viewport={"width": 1440, "height": 960})
        desktop.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            and "status of 401" not in message.text
            else None,
        )
        desktop.goto("http://127.0.0.1:8765/")
        desktop.wait_for_load_state("networkidle")
        desktop.locator("#auth-view").wait_for(state="visible")
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-auth-desktop.png"),
            full_page=True,
        )

        desktop.locator("#login-form input[name=identifier]").fill("ui-admin@example.test")
        desktop.locator("#login-form input[name=password]").fill("UiAdminPass!2026")
        desktop.locator("#login-form button[type=submit]").click()
        desktop.locator("#workspace").wait_for(state="visible")
        if desktop.locator("#auth-error").is_visible():
            raise AssertionError(
                f"Login failed in browser: {desktop.locator('#auth-error').inner_text()}"
            )
        desktop.locator("#admin-nav").click()
        desktop.locator("#admin-view").wait_for(state="visible")
        desktop.locator("#settings-model").wait_for(state="visible")
        desktop.wait_for_function(
            "() => !document.querySelector('#model-meta').textContent.includes('Načítavam')"
        )
        orders_table = desktop.locator("#data-schema-tables").get_by_text(
            "orders", exact=True
        )
        assert orders_table.count() == 1, {
            "toasts": desktop.locator(".toast").all_inner_texts(),
            "schema": desktop.locator("#data-schema-tables").inner_text(),
        }
        desktop.locator("#admin-user-name").fill("UI Operations")
        desktop.locator("#admin-user-password-generate").click()
        generated_password = desktop.locator("#admin-user-password").input_value()
        assert len(generated_password) == 18
        assert any(character.islower() for character in generated_password)
        assert any(character.isupper() for character in generated_password)
        assert any(character.isdigit() for character in generated_password)
        assert desktop.locator("#admin-user-password-copy").is_enabled()
        desktop.locator("#admin-user-role").select_option("admin")
        desktop.locator("#admin-user-create-form button[type=submit]").click()
        created_account = desktop.locator("#users-table").get_by_text(
            "Prihlásenie: UI Operations", exact=True
        )
        created_account.wait_for(state="visible")
        desktop.locator("#rag-file").set_input_files(
            [
                {
                    "name": "ui-runbook.md",
                    "mimeType": "text/markdown",
                    "buffer": b"# Nexus\nNexus health endpoint is /health.",
                },
                {
                    "name": "ui-policy.txt",
                    "mimeType": "text/plain",
                    "buffer": b"Production changes require an approved maintenance window.",
                },
            ]
        )
        desktop.get_by_text("ui-runbook.md", exact=True).wait_for(state="visible")
        desktop.get_by_text("ui-policy.txt", exact=True).wait_for(state="visible")
        desktop.locator("#rag-drop").evaluate(
            """drop => {
              const data = new DataTransfer();
              data.items.add(new File(
                ['Database restore steps are tested quarterly.'],
                'ui-dropped-runbook.md',
                {type: 'text/markdown'}
              ));
              drop.dispatchEvent(new DragEvent('dragenter', {
                bubbles: true, cancelable: true, dataTransfer: data
              }));
              if (!drop.classList.contains('dragging')) {
                throw new Error('Drop target did not enter dragging state');
              }
              drop.dispatchEvent(new DragEvent('drop', {
                bubbles: true, cancelable: true, dataTransfer: data
              }));
            }"""
        )
        desktop.get_by_text("ui-dropped-runbook.md", exact=True).wait_for(
            state="visible"
        )
        desktop.locator(".admin-card--infra .switch").click()
        desktop.locator('.nav-item[data-view="chat"]').click()
        desktop.locator("#infra-agent-option").wait_for(state="visible")
        desktop.locator("#data-agent-option").wait_for(state="visible")
        desktop.locator("#admin-nav").click()
        layout = desktop.evaluate(
            """() => ({
              viewport: innerWidth,
              scrollWidth: document.documentElement.scrollWidth,
              widest: [...document.querySelectorAll('body *')]
                .map(el => ({tag: el.tagName, id: el.id, cls: el.className,
                  right: Math.round(el.getBoundingClientRect().right),
                  width: Math.round(el.getBoundingClientRect().width)}))
                .filter(x => x.right > innerWidth + 2)
                .sort((a, b) => b.right - a.right).slice(0, 5)
            })"""
        )
        assert layout["scrollWidth"] <= layout["viewport"] + 2, layout
        desktop.locator(".toast").last.wait_for(state="hidden")
        desktop.evaluate("document.querySelector('#admin-view').scrollTop = 0")
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-admin-desktop.png"),
            full_page=True,
        )
        desktop.locator(".admin-card--data").scroll_into_view_if_needed()
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-data-agent-desktop.png"),
            full_page=False,
        )

        desktop.set_viewport_size({"width": 390, "height": 844})
        desktop.evaluate("document.querySelector('#admin-view').scrollTop = 0")
        desktop.wait_for_function(
            "() => getComputedStyle(document.querySelector('#sidebar-scrim')).display === 'none'"
        )
        hit_target = desktop.evaluate(
            """() => {
              const button = document.querySelector('#sidebar-open');
              const box = button.getBoundingClientRect();
              const hit = document.elementFromPoint(
                box.left + box.width / 2,
                box.top + box.height / 2
              );
              return {id: hit?.id || '', className: hit?.className || ''};
            }"""
        )
        assert hit_target["id"] == "sidebar-open", hit_target

        desktop.locator("#sidebar-open").click()
        desktop.wait_for_function(
            "() => document.querySelector('#sidebar').classList.contains('open')"
        )
        assert desktop.locator("#sidebar-open").get_attribute("aria-expanded") == "true"
        desktop.locator('.nav-item[data-view="chat"]').click()
        desktop.wait_for_function(
            "() => !document.querySelector('#sidebar').classList.contains('open')"
        )
        desktop.locator("#data-agent-option").click()
        assert (
            desktop.locator("#data-agent-option").get_attribute("aria-pressed")
            == "true"
        )
        desktop.locator("#message-input").fill("Sprav report tržieb podľa krajín.")
        desktop.locator("#composer").evaluate("form => form.requestSubmit()")
        desktop.locator(".message--assistant").wait_for(state="visible")
        desktop.locator(".message__sql").wait_for(state="visible")
        desktop.locator(".message__sql summary").click()
        desktop.locator(".message__sql code").wait_for(state="visible")
        assert "SELECT" in desktop.locator(".message__sql code").inner_text().upper()
        data_title = desktop.locator("#conversation-title").inner_text()
        assert desktop.locator("#conversation-count").inner_text() == "1"
        assert desktop.locator("#conversation-heading-label").inner_text() == "DATA HISTÓRIA"

        desktop.locator('.agent-option[data-agent="general"]').click()
        desktop.locator("#empty-state").wait_for(state="visible")
        assert desktop.locator("#conversation-count").inner_text() == "0"
        assert desktop.locator("#conversation-heading-label").inner_text() == "NEXUS HISTÓRIA"
        assert desktop.locator(".message").count() == 0

        desktop.locator("#infra-agent-option").click()
        desktop.wait_for_function(
            "() => document.querySelector('#conversation-heading-label').textContent === 'INFRA HISTÓRIA'"
        )
        desktop.locator("#infra-source-switcher").wait_for(state="visible")
        assert (
            desktop.locator(
                '.infra-source-option[data-infra-source="snapshot"]'
            ).get_attribute("aria-pressed")
            == "true"
        )
        desktop.locator(
            '.infra-source-option[data-infra-source="live"]'
        ).click()
        desktop.wait_for_function(
            "() => document.querySelector('#current-section').textContent === 'INFRA LIVE'"
        )
        assert (
            desktop.locator(
                '.infra-source-option[data-infra-source="live"]'
            ).get_attribute("aria-pressed")
            == "true"
        )
        assert desktop.locator("#conversation-count").inner_text() == "0"
        assert desktop.locator("#conversation-heading-label").inner_text() == "INFRA HISTÓRIA"
        infra_empty_title = desktop.locator("#empty-title-lead").inner_text()
        assert "serveri" in infra_empty_title.lower(), repr(infra_empty_title)
        desktop.locator("#message-input").fill("Je Nexus služba online?")
        desktop.locator("#composer").evaluate("form => form.requestSubmit()")
        desktop.locator(".message--assistant").wait_for(state="visible")
        desktop.locator(".source-infra-live").wait_for(state="visible")
        assert "LIVE SERVER" in desktop.locator(".source-infra-live").inner_text()
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-infra-live-mobile.png"),
            full_page=False,
        )
        infra_title = desktop.locator("#conversation-title").inner_text()
        assert desktop.locator("#conversation-count").inner_text() == "1"
        desktop.locator(
            '.infra-source-option[data-infra-source="snapshot"]'
        ).click()
        assert (
            desktop.locator(
                '.infra-source-option[data-infra-source="snapshot"]'
            ).get_attribute("aria-pressed")
            == "true"
        )

        desktop.locator("#data-agent-option").click()
        desktop.locator(".message__sql").wait_for(state="visible")
        assert desktop.locator("#conversation-title").inner_text() == data_title
        assert desktop.locator("#conversation-count").inner_text() == "1"
        assert desktop.locator(".message--assistant").count() == 1

        desktop.locator("#infra-agent-option").click()
        desktop.locator(".message--assistant").wait_for(state="visible")
        assert desktop.locator("#conversation-title").inner_text() == infra_title
        assert desktop.locator("#conversation-count").inner_text() == "1"

        desktop.locator("#data-agent-option").click()
        desktop.locator(".message__sql").wait_for(state="visible")
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-chat-mobile.png"),
            full_page=False,
        )

        desktop.locator("#sidebar-open").click()
        desktop.locator("#admin-nav").click()
        desktop.locator("#admin-view").wait_for(state="visible")
        desktop.wait_for_function(
            """() => {
              const sidebar = document.querySelector('#sidebar');
              return !sidebar.classList.contains('open')
                && sidebar.getBoundingClientRect().right <= 1
                && document.querySelector('#admin-view').getAttribute('aria-busy') === 'false';
            }"""
        )
        table_layout = desktop.locator(".admin-card--users .table-wrap").evaluate(
            "(element) => ({clientWidth: element.clientWidth, scrollWidth: element.scrollWidth})"
        )
        assert table_layout["scrollWidth"] <= table_layout["clientWidth"] + 2, table_layout
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-admin-mobile.png"),
            full_page=False,
        )
        desktop.locator(".admin-card--data").scroll_into_view_if_needed()
        desktop.screenshot(
            path=str(OUTPUT_DIR / "nexus-data-agent-mobile.png"),
            full_page=False,
        )
        browser.close()

        assert not console_errors, f"Browser console errors: {console_errors}"
        print(
            "UI smoke test passed: auth, separate Nexus/Infra/Data histories, "
            "Infra LIVE/SNAPSHOT, admin, model routing, RAG, reports, "
            "desktop and mobile."
        )


if __name__ == "__main__":
    run()
