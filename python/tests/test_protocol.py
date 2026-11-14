import json
import unittest

from discord_adapter.protocol import (
    PROTOCOL_VERSION,
    decode_response,
    encode_request,
)


class ProtocolTests(unittest.TestCase):

    def test_encode_request(self):

        encoded = encode_request(
            "req-1",
            "system.health",
            {"source": "test"},
        )

        message = json.loads(encoded)

        self.assertEqual(
            message["protocol_version"],
            PROTOCOL_VERSION,
        )

        self.assertEqual(
            message["request_id"],
            "req-1",
        )

        self.assertEqual(
            message["kind"],
            "request",
        )

        self.assertEqual(
            message["operation"],
            "system.health",
        )

        self.assertEqual(
            message["payload"],
            {"source": "test"},
        )

    def test_empty_identifiers_are_rejected(self):

        with self.assertRaises(ValueError):
            encode_request(
                "",
                "system.health",
            )

        with self.assertRaises(ValueError):
            encode_request(
                "req-1",
                "",
            )

    def test_decode_response(self):

        response = decode_response(
            '{"protocol_version":1,'
            '"request_id":"req-1",'
            '"ok":true,'
            '"payload":{"status":"ok"}}'
        )

        self.assertTrue(response.ok)

        self.assertEqual(
            response.request_id,
            "req-1",
        )

        self.assertEqual(
            response.payload,
            {"status": "ok"},
        )

    def test_wrong_protocol_is_rejected(self):

        with self.assertRaises(ValueError):

            decode_response(
                '{"protocol_version":2,'
                '"request_id":"req-1",'
                '"ok":true}'
            )


if __name__ == "__main__":
    unittest.main()
