from datetime import timedelta
from importlib.util import find_spec
from pathlib import Path
from tempfile import gettempdir
from unittest import skipUnless
from urllib.parse import urlparse

from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts import mfa, totp
from apps.accounts.models import User
from apps.accounts.security import axes_lockout_response
from apps.hub.models import OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, PlatformAccess


class RegaroAuthFlowTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self):
        cache.clear()
        self.office = Organization.objects.create(name="Escritório Exemplo", slug="auth-review")
        self.user = User.objects.create_user("auth-review@example.test", "test-password-123456")
        Membership.objects.create(
            user=self.user, organization=self.office, role=Membership.Role.OWNER
        )
        self.profile = OfficeProfile.objects.create(
            organization=self.office, trial_started_at=timezone.now(), require_mfa=True
        )

    def test_trial_exemption_expires_and_cannot_override_platform(self):
        self.assertFalse(mfa.is_required(self.user))
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("hub:dashboard")).status_code, 200)
        self.profile.trial_started_at = timezone.now() - timedelta(days=14)
        self.profile.save()
        self.assertTrue(mfa.is_required(self.user))
        self.assertIn(
            reverse("accounts:mfa-setup"), self.client.get(reverse("hub:dashboard"))["Location"]
        )
        self.profile.trial_started_at = timezone.now()
        self.profile.contract_status = OfficeProfile.ContractStatus.ACTIVE
        self.profile.save()
        self.assertTrue(mfa.is_required(self.user))
        self.profile.contract_status = OfficeProfile.ContractStatus.TRIAL
        self.profile.save()
        PlatformAccess.objects.create(user=self.user, role=PlatformAccess.Role.SUPPORT)
        self.assertTrue(mfa.is_required(self.user))

    def test_mfa_setup_preserves_secret_on_post_and_destination(self):
        self.client.force_login(self.user)
        target = reverse("hub:companies")
        self.client.get(reverse("accounts:mfa-setup"), {"next": target})
        device = mfa.device_for(self.user)
        secret = device.secret
        response = self.client.post(
            reverse("accounts:mfa-setup"),
            {"code": totp.code_for(secret, totp.counter_at()), "next": target},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guarde estes códigos")
        self.assertContains(response, f'href="{target}"')
        device.refresh_from_db()
        self.assertEqual(device.secret, secret)
        self.assertTrue(device.is_confirmed)
        follow_up = self.client.get(target)
        self.assertEqual(follow_up.status_code, 200)
        self.assertNotIn(reverse("accounts:mfa-verify"), follow_up.get("Location", ""))

    def test_platform_operator_can_leave_recovery_screen_for_console(self):
        PlatformAccess.objects.create(user=self.user, role=PlatformAccess.Role.DEVELOPER)
        self.client.force_login(self.user)
        self.client.get(reverse("accounts:mfa-setup"), {"next": reverse("hub:dashboard")})
        device = mfa.device_for(self.user)
        response = self.client.post(
            reverse("accounts:mfa-setup"),
            {
                "code": totp.code_for(device.secret, totp.counter_at()),
                "next": reverse("hub:dashboard"),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("platform:dashboard")}"')
        self.assertContains(response, "Ir às configurações da Mewstack")
        self.assertEqual(self.client.get(reverse("platform:dashboard")).status_code, 200)

    def test_recovery_continue_has_navigable_url_when_setup_has_no_next(self):
        PlatformAccess.objects.create(user=self.user, role=PlatformAccess.Role.DEVELOPER)
        self.client.force_login(self.user)
        self.client.get(reverse("accounts:mfa-setup"))
        device = mfa.device_for(self.user)
        response = self.client.post(
            reverse("accounts:mfa-setup"),
            {"code": totp.code_for(device.secret, totp.counter_at())},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("platform:dashboard")}"')
        self.assertNotContains(response, 'href="platform:dashboard"')
        self.assertEqual(self.client.get(reverse("platform:configuration")).status_code, 200)

    def test_invitation_activation_starts_trial_once(self):
        office = Organization.objects.create(name="Novo escritório", slug="new-auth-review")
        token, digest = Invitation.issue_token()
        invitation = Invitation.objects.create(
            organization=office,
            email="new-auth@example.test",
            role=Membership.Role.OWNER,
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=2),
        )
        response = self.client.post(
            reverse("hub:activate", args=[token]),
            {"password": "a-safe-password-12345", "password_confirm": "a-safe-password-12345"},
        )
        self.assertEqual(response.status_code, 302)
        profile = OfficeProfile.objects.get(organization=office)
        self.assertIsNotNone(profile.trial_started_at)
        start = profile.trial_started_at
        self.assertFalse(mfa.is_required(User.objects.get(email=invitation.email)))
        self.assertEqual(self.client.post(reverse("hub:activate", args=[token])).status_code, 410)
        profile.refresh_from_db()
        self.assertEqual(profile.trial_started_at, start)

    def test_web_lockout_is_html_api_lockout_stays_json(self):
        response = axes_lockout_response(RequestFactory().post(reverse("hub:login")), None, {})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "CICA", status_code=429)
        response = axes_lockout_response(RequestFactory().post("/api/v1/auth/login/"), None, {})
        self.assertIn("application/json", response["Content-Type"])

    @skipUnless(
        find_spec("playwright") is not None,
        "Python Playwright is optional; browser coverage runs via Playwright MCP.",
    )
    def test_auth_screens_render_and_interact(self):
        from playwright.sync_api import sync_playwright

        pages = {}
        pages["login"] = self.client.get(reverse("hub:login")).content
        pages["login-error"] = self.client.post(
            reverse("hub:login"),
            {
                "username": "missing@example.test",
                "password": "wrong",
                "next": reverse("hub:companies"),
            },
        ).content
        pages["proposal"] = self.client.get(reverse("hub:signup")).content
        pages["proposal-error"] = self.client.post(
            reverse("hub:signup"), {"contact_email": "invalid"}
        ).content
        pages["invalid-invite"] = self.client.get(reverse("hub:activate", args=["invalid"])).content
        token, digest = Invitation.issue_token()
        invitation = Invitation.objects.create(
            organization=self.office,
            email="invite-review@example.test",
            role=Membership.Role.OPERATOR,
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=1),
        )
        pages["activation"] = self.client.get(reverse("hub:activate", args=[token])).content
        pages["activation-error"] = self.client.post(
            reverse("hub:activate", args=[token]),
            {"password": "long-enough-password", "password_confirm": "different-password"},
        ).content
        invitation.email = self.user.email
        invitation.save()
        pages["invite-signin"] = self.client.get(reverse("hub:activate", args=[token])).content
        self.client.force_login(self.user)
        pages["invite-accept"] = self.client.get(reverse("hub:activate", args=[token])).content
        pages["mfa-setup"] = self.client.get(reverse("accounts:mfa-setup")).content
        qr = self.client.get(reverse("accounts:mfa-qr")).content
        device = mfa.device_for(self.user)
        mfa.confirm_enrollment(device, totp.code_for(device.secret, totp.counter_at()))
        pages["mfa-verify"] = self.client.get(reverse("accounts:mfa-verify")).content
        pages["mfa-error"] = self.client.post(
            reverse("accounts:mfa-verify"), {"code": "invalid"}
        ).content
        pages["recovery"] = render_to_string(
            "accounts/mfa_recovery.html", {"codes": ["test-only-01", "test-only-02"]}
        ).encode()
        pages["no-office"] = render_to_string("hub/no_office.html").encode()
        pages["forbidden"] = render_to_string("hub/forbidden.html").encode()
        pages["locked"] = render_to_string("hub/login_locked.html", {"retry_minutes": 30}).encode()
        current = ["login"]
        registry = [
            {
                "status": "found",
                "razao_social": "Empresa Exemplo",
                "municipio": "São Paulo",
                "uf": "SP",
            }
        ]

        def route_local(route):
            path = urlparse(route.request.url).path
            if path == "/proposta/cnpj/":
                import json

                route.fulfill(body=json.dumps(registry[0]), content_type="application/json")
            elif path.startswith("/static/"):
                found = finders.find(path.removeprefix("/static/"))
                route.fulfill(
                    body=Path(found).read_bytes() if found else b"",
                    content_type="text/css" if path.endswith(".css") else "application/javascript",
                    status=200 if found else 404,
                )
            elif path.endswith("qr.svg"):
                route.fulfill(body=qr, content_type="image/svg+xml")
            else:
                route.fulfill(body=pages[current[0]], content_type="text/html")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", route_local)
            for name in pages:
                current[0] = name
                for width in [1440, 390]:
                    page.set_viewport_size({"width": width, "height": 1000})
                    page.emulate_media(color_scheme="dark")
                    page.goto("http://regaro.test/" + name)
                    self.assertTrue(
                        page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
                    )
                    self.assertEqual(page.locator("h1").count(), 1, name)
                    self.assertNotIn("HubContador", page.locator("body").inner_text())
                    if page.locator("[data-form-errors]").count():
                        self.assertTrue(
                            page.locator("[data-form-errors]").evaluate(
                                "(e)=>e===document.activeElement"
                            ),
                            name,
                        )
                    # Never capture QR/secret screenshots, even for test fixtures.
                    if name != "mfa-setup":
                        page.screenshot(
                            path=str(Path(gettempdir()) / f"regaro-auth-{name}-{width}.png")
                        )
            current[0] = "login"
            page.goto("http://regaro.test/login")
            page.locator("#id_password").fill("local-test")
            page.locator("[data-password-toggle]").click()
            self.assertEqual(page.locator("#id_password").get_attribute("type"), "text")
            page.locator("[data-password-toggle]").click()
            self.assertEqual(page.locator("#id_password").get_attribute("type"), "password")
            current[0] = "proposal"
            page.goto("http://regaro.test/proposta/")
            page.locator("#id_full_name").fill("Pessoa Teste")
            page.locator("#id_email").fill("pessoa@example.test")
            page.locator("#id_cnpj").fill("19131243000197")
            page.wait_for_function(
                "document.getElementById('registry-name').textContent === 'Empresa Exemplo'"
            )
            self.assertIn("São Paulo", page.locator("#registry-place").inner_text())
            page.screenshot(path=str(Path(gettempdir()) / "regaro-auth-cnpj-found.png"))
            registry[0] = {"status": "unavailable"}
            page.locator("#id_cnpj").fill("00000000E08G12")
            page.wait_for_function(
                "document.getElementById('registry-status').textContent.includes('indisponível')"
            )
            self.assertEqual(page.locator("#registry-name").inner_text(), "")
            page.locator("#id_cnpj").fill("123")
            self.assertTrue(page.locator("#registry-result").is_hidden())
            self.assertEqual(errors, [])
            browser.close()
