import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import RemoteApiConfig
from services import RemoteApiClient, RemoteApiResponseError, RemoteApiSession


class FakeResponse:
    def __init__(self, payload, headers=None):
        self.payload = payload
        self.headers = headers or {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


class RemoteApiClientTests(unittest.TestCase):
    def test_login_stores_session_from_response_envelope(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080", timeout_seconds=3))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse(
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "accessToken": "access-token",
                        "refreshToken": "refresh-token",
                        "tokenType": "bearer",
                    },
                }
            )

            session = client.login("operator", "secret")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:18080/api/v1/auth/login")
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"username": "operator", "password": "secret"})
        self.assertEqual(session.access_token, "access-token")
        self.assertEqual(client.session, session)

    def test_list_inventory_items_sends_bearer_token_and_clean_query(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080/", timeout_seconds=3))
        client.set_session(RemoteApiSession("access-token", "refresh-token"))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse({"code": 200, "message": "success", "data": []})

            items = client.list_inventory_items(
                {
                    "inventoryType": "leftover",
                    "status": "available",
                    "reusable": True,
                    "materialGrade": "",
                    "thickness": None,
                }
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(items, [])
        self.assertIn("inventoryType=leftover", request.full_url)
        self.assertIn("status=available", request.full_url)
        self.assertIn("reusable=true", request.full_url)
        self.assertNotIn("materialGrade", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer access-token")

    def test_page_inventory_items_uses_page_endpoint_and_meta(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080/", timeout_seconds=3))
        client.set_session(RemoteApiSession("access-token", "refresh-token"))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse(
                {
                    "code": 200,
                    "message": "success",
                    "data": {
                        "items": [],
                        "meta": {"page": 2, "pageSize": 20, "total": 45},
                    },
                }
            )

            page_data = client.page_inventory_items({"inventoryType": "leftover"}, page=2, page_size=20)

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/inventory-items/page", request.full_url)
        self.assertIn("inventoryType=leftover", request.full_url)
        self.assertIn("page=2", request.full_url)
        self.assertIn("pageSize=20", request.full_url)
        self.assertEqual(page_data["meta"]["total"], 45)

    def test_get_inventory_item_by_code_uses_code_endpoint(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080/", timeout_seconds=3))
        client.set_session(RemoteApiSession("access-token", "refresh-token"))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse(
                {
                    "code": 200,
                    "message": "success",
                    "data": {"id": 10, "inventoryCode": "RM:CODE"},
                }
            )

            item = client.get_inventory_item_by_code("RM:CODE")

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/inventory-items/by-code", request.full_url)
        self.assertIn("inventoryCode=RM%3ACODE", request.full_url)
        self.assertEqual(item["id"], 10)

    def test_preview_inventory_xlsx_sends_multipart_file(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080/", timeout_seconds=3))
        client.set_session(RemoteApiSession("access-token", "refresh-token"))

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "inventory.xlsx"
            file_path.write_bytes(b"xlsx")
            with patch("services.remote_api.urlopen") as urlopen:
                urlopen.return_value = FakeResponse(
                    {
                        "code": 200,
                        "message": "success",
                        "data": {"dryRun": True, "totalRows": 1, "validRows": 1, "created": 1, "updated": 0, "skipped": 0},
                    }
                )

                result = client.preview_inventory_xlsx(str(file_path))

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/inventory-items/import-xlsx", request.full_url)
        self.assertIn("dryRun=true", request.full_url)
        self.assertIn("multipart/form-data", request.headers["Content-type"])
        self.assertIn(b'name="file"; filename="inventory.xlsx"', request.data)
        self.assertTrue(result["dryRun"])

    def test_export_inventory_xlsx_returns_binary_content(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080/", timeout_seconds=3))
        client.set_session(RemoteApiSession("access-token", "refresh-token"))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse(
                b"xlsx-bytes",
                headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
            )

            content = client.export_inventory_xlsx(["RM:CODE"])

        request = urlopen.call_args.args[0]
        self.assertIn("/api/v1/inventory-items/export-xlsx", request.full_url)
        self.assertEqual(json.loads(request.data.decode("utf-8")), {"inventoryCodes": ["RM:CODE"]})
        self.assertEqual(content, b"xlsx-bytes")

    def test_business_error_raises_response_error(self):
        client = RemoteApiClient(RemoteApiConfig(base_url="http://localhost:18080", timeout_seconds=3))

        with patch("services.remote_api.urlopen") as urlopen:
            urlopen.return_value = FakeResponse(
                {
                    "code": 400,
                    "message": "business_error",
                    "data": None,
                    "errorCode": "duplicate_material",
                }
            )

            with self.assertRaises(RemoteApiResponseError) as context:
                client.health()

        self.assertEqual(context.exception.error_code, "duplicate_material")


if __name__ == "__main__":
    unittest.main()
