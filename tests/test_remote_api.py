import json
import unittest
from unittest.mock import patch

from config import RemoteApiConfig
from services import RemoteApiClient, RemoteApiResponseError, RemoteApiSession


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
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
