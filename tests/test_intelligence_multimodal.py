from __future__ import annotations

import json
import os
from base64 import b64decode, b64encode
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Thread
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.test import SimpleTestCase
from PIL import Image

from apps.intelligence.multimodal import (
    MAX_REQUEST_BYTES,
    MultimodalError,
    MultimodalRequestHandler,
    MultimodalResult,
    _image_to_jpeg_base64,
    _ollama_url,
    _pdf_page_images,
    analyze_document,
    analyze_payload,
    document_images,
    run_server,
)


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return json.dumps(self.payload).encode()


class LocalMultimodalAdapterTests(SimpleTestCase):
    def test_local_image_conversion_removes_original_format_and_bounds_output(self) -> None:
        source = BytesIO()
        Image.new("RGBA", (32, 24), color=(10, 20, 30, 128)).save(source, format="PNG")

        encoded = _image_to_jpeg_base64(source.getvalue())

        self.assertTrue(b64decode(encoded).startswith(b"\xff\xd8"))
        self.assertEqual(
            document_images(content=source.getvalue(), content_type="image/png"), [encoded]
        )
        with self.assertRaises(MultimodalError):
            _image_to_jpeg_base64(b"not-an-image")

    def test_private_adapter_accepts_only_valid_document_payloads(self) -> None:
        request = {
            "name": "nota.png",
            "content_type": "image/png",
            "content_b64": b64encode(b"image").decode(),
        }
        with patch(
            "apps.intelligence.multimodal.analyze_document",
            return_value=MultimodalResult(analysis="Fato local.", pages_analyzed=1),
        ):
            self.assertEqual(
                analyze_payload(request),
                {"analysis": "Fato local.", "pages_analyzed": 1},
            )
        with self.assertRaises(MultimodalError):
            analyze_payload({**request, "content_b64": "!"})

    def test_private_http_surface_serves_health_and_bounded_document_analysis(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), MultimodalRequestHandler)
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        address = f"http://127.0.0.1:{server.server_port}"
        payload = json.dumps(
            {
                "name": "nota.png",
                "content_type": "image/png",
                "content_b64": b64encode(b"image").decode(),
            }
        ).encode()
        try:
            with urlopen(f"{address}/healthz") as response:  # noqa: S310 - local test server
                self.assertEqual(json.loads(response.read()), {"status": "ok"})
            with self.assertRaises(HTTPError) as missing:
                urlopen(f"{address}/missing")  # noqa: S310 - local test server
            self.assertEqual(missing.exception.code, 404)
            with patch(
                "apps.intelligence.multimodal.analyze_document",
                return_value=MultimodalResult(analysis="Fato local.", pages_analyzed=1),
            ):
                request = Request(  # noqa: S310 - local test server
                    f"{address}/v1/analyze-document",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request) as response:  # noqa: S310 - local test server
                    self.assertEqual(json.loads(response.read())["analysis"], "Fato local.")
            with self.assertRaises(HTTPError) as error:
                urlopen(  # noqa: S310 - local test server
                    Request(  # noqa: S310 - local test server
                        f"{address}/v1/analyze-document",
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                )
            self.assertEqual(error.exception.code, 422)
            with self.assertRaises(HTTPError) as wrong_method_path:
                urlopen(  # noqa: S310 - local test server
                    Request(  # noqa: S310 - local test server
                        f"{address}/missing",
                        data=b"{}",
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                )
            self.assertEqual(wrong_method_path.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_private_server_rejects_an_invalid_port_before_opening_a_socket(self) -> None:
        previous_port = os.environ.get("MULTIMODAL_PORT")
        os.environ["MULTIMODAL_PORT"] = "not-a-port"
        try:
            with self.assertRaises(RuntimeError):
                run_server()
        finally:
            if previous_port is None:
                os.environ.pop("MULTIMODAL_PORT", None)
            else:
                os.environ["MULTIMODAL_PORT"] = previous_port

    def test_rejects_unsupported_or_oversized_input_before_image_processing(self) -> None:
        with self.assertRaises(MultimodalError):
            document_images(content=b"texto", content_type="text/plain")
        with self.assertRaises(MultimodalError):
            document_images(content=b"x" * (MAX_REQUEST_BYTES + 1), content_type="image/png")

    @patch("apps.intelligence.multimodal.urlopen")
    @patch("apps.intelligence.multimodal.document_images", return_value=["page-base64"])
    def test_only_rasterized_pages_are_sent_to_private_ollama(
        self, mocked_images, mocked_urlopen
    ) -> None:
        mocked_urlopen.return_value = _Response(
            {"message": {"content": "Fato fiscal verificável."}}
        )

        result = analyze_document(
            content=b"raw-pdf-must-not-be-in-payload",
            content_type="application/pdf",
            name="apuração.pdf",
        )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        serialized = json.dumps(payload)
        self.assertEqual(result.analysis, "Fato fiscal verificável.")
        self.assertEqual(result.pages_analyzed, 1)
        self.assertEqual(payload["messages"][1]["images"], ["page-base64"])
        self.assertNotIn("raw-pdf-must-not-be-in-payload", serialized)
        self.assertFalse(payload["stream"])
        mocked_images.assert_called_once_with(
            content=b"raw-pdf-must-not-be-in-payload", content_type="application/pdf"
        )

    def test_local_model_origin_is_validated_before_any_request(self) -> None:
        previous_endpoint = os.environ.get("OLLAMA_ENDPOINT")
        os.environ["OLLAMA_ENDPOINT"] = "file:///unsafe"
        try:
            with self.assertRaises(MultimodalError):
                _ollama_url()
        finally:
            if previous_endpoint is None:
                os.environ.pop("OLLAMA_ENDPOINT", None)
            else:
                os.environ["OLLAMA_ENDPOINT"] = previous_endpoint

    @patch("apps.intelligence.multimodal.document_images", return_value=["page-base64"])
    @patch("apps.intelligence.multimodal.urlopen", side_effect=URLError("offline"))
    def test_model_transport_failure_is_a_bounded_adapter_error(
        self, _mocked_urlopen, _mocked_images
    ) -> None:
        with self.assertRaises(MultimodalError):
            analyze_document(content=b"image", content_type="image/png", name="nota.png")

    @patch("apps.intelligence.multimodal._image_to_jpeg_base64", return_value="page-base64")
    @patch("apps.intelligence.multimodal.subprocess.run")
    def test_pdf_conversion_uses_only_a_bounded_local_temporary_page_set(
        self, mocked_run, mocked_encoder
    ) -> None:
        def create_page(command, **_kwargs) -> None:
            prefix = command[-1]
            with open(f"{prefix}-1.jpg", "wb") as page:
                page.write(b"local-page")

        mocked_run.side_effect = create_page

        pages = _pdf_page_images(b"%PDF-local-only")

        self.assertEqual(pages, ["page-base64"])
        self.assertEqual(mocked_run.call_args.args[0][0], "pdftoppm")
        mocked_encoder.assert_called_once()

    @patch("apps.intelligence.multimodal.document_images", return_value=["page-base64"])
    @patch("apps.intelligence.multimodal.urlopen")
    def test_invalid_model_payload_does_not_become_evidence(
        self, mocked_urlopen, _mocked_images
    ) -> None:
        mocked_urlopen.return_value = _Response({"message": {"content": ""}})

        with self.assertRaises(MultimodalError):
            analyze_document(content=b"image", content_type="image/png", name="nota.png")
