from __future__ import annotations

import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from apps.accounts.models import User
from apps.common.views import bad_request, permission_denied, server_error
from config import urls as root_urls


@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def assert_private_error_headers(self, response: HttpResponse) -> None:
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_anonymous_404_is_branded_recoverable_and_keeps_real_status(self) -> None:
        response = self.client.get("/missing/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Não encontramos este conteúdo", status_code=404)
        self.assertContains(response, "Ir para a página inicial", status_code=404)
        self.assertNotContains(response, "private", status_code=404)
        self.assert_private_error_headers(response)

    def test_authenticated_404_returns_to_workspace_without_revealing_resource(self) -> None:
        user = User.objects.create_user("error-page@example.test", "test-password-123")
        self.client.force_login(user)

        response = self.client.get("/missing-private-record/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Voltar ao escritório", status_code=404)
        self.assertNotContains(response, "permissão", status_code=404)
        self.assert_private_error_headers(response)

    def test_permission_denied_does_not_reflect_exception_details(self) -> None:
        request = RequestFactory().get("/protected/")
        request.user = AnonymousUser()
        response = permission_denied(request, PermissionError("private permission details"))

        self.assertEqual(response.status_code, 403)
        self.assertIn("Você não pode abrir esta área", response.content.decode())
        self.assertNotIn("private permission details", response.content.decode())
        self.assert_private_error_headers(response)

    def test_server_error_is_recoverable_and_does_not_expose_exception(self) -> None:
        request = RequestFactory().get("/failing-page/")
        request.user = AnonymousUser()
        response = server_error(request)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Não foi possível concluir agora", response.content.decode())
        self.assertIn("Tentar novamente", response.content.decode())
        self.assertNotIn("exception", response.content.decode())
        self.assert_private_error_headers(response)

    def test_server_error_has_template_independent_final_fallback(self) -> None:
        request = RequestFactory().get("/failing-page/")
        request.user = AnonymousUser()

        with patch(
            "apps.common.views._render_error_page",
            side_effect=RuntimeError("private template failure"),
        ):
            response = server_error(request)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Não foi possível concluir agora", response.content.decode())
        self.assertNotIn("private template failure", response.content.decode())
        self.assert_private_error_headers(response)

    def test_api_errors_stay_json(self) -> None:
        not_found = self.client.get("/api/missing/")

        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(not_found.json(), {"detail": "Não encontrado."})
        self.assert_private_error_headers(not_found)

        request = RequestFactory().get("/api/invalid/")
        invalid = bad_request(request, ValueError("private bad request"))
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(
            json.loads(invalid.content), {"detail": "Solicitação inválida."}
        )
        self.assert_private_error_headers(invalid)

    def test_root_urlconf_registers_all_error_handlers(self) -> None:
        self.assertEqual(root_urls.handler400, "apps.common.views.bad_request")
        self.assertEqual(root_urls.handler403, "apps.common.views.permission_denied")
        self.assertEqual(root_urls.handler404, "apps.common.views.page_not_found")
        self.assertEqual(root_urls.handler500, "apps.common.views.server_error")
