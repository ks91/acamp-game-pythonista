import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from toolkit.api_client import ApiClient


class RecordingHandler(BaseHTTPRequestHandler):
    request_path = None
    authorization = None
    payload = None

    def do_GET(self):
        type(self).request_path = self.path
        type(self).authorization = self.headers.get("Authorization")
        body = b'{"team_id":"green","location_event_count":1,"latest_location":null}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        type(self).request_path = self.path
        type(self).authorization = self.headers.get("Authorization")
        type(self).payload = json.loads(self.rfile.read(content_length))
        body = b'{"accepted":true,"event_id":1}'
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class ApiClientTests(unittest.TestCase):
    def setUp(self):
        RecordingHandler.request_path = None
        RecordingHandler.authorization = None
        RecordingHandler.payload = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_post_location_sample_uses_v1_endpoint_and_team_bearer_token(self):
        host, port = self.server.server_address
        client = ApiClient(
            base_url="http://{}:{}/v1".format(host, port),
            token="team-token",
        )

        result = client.post_location_sample(
            {
                "team_id": "green",
                "device_id": "green-ipad",
                "client_time": "2026-09-20T10:00:00+09:00",
                "latitude": 35.3387,
                "longitude": 139.4888,
                "accuracy_m": 18.5,
            }
        )

        self.assertEqual({"accepted": True, "event_id": 1}, result)
        self.assertEqual("/v1/location-samples", RecordingHandler.request_path)
        self.assertEqual("Bearer team-token", RecordingHandler.authorization)
        self.assertEqual("green", RecordingHandler.payload["team_id"])
    def test_get_team_state_uses_team_bearer_token(self):
        host, port = self.server.server_address
        client = ApiClient(
            base_url="http://{}:{}/v1".format(host, port),
            token="team-token",
        )

        result = client.get_team_state()

        self.assertEqual("green", result["team_id"])
        self.assertEqual("/v1/team/state", RecordingHandler.request_path)
        self.assertEqual("Bearer team-token", RecordingHandler.authorization)


if __name__ == "__main__":
    unittest.main()
