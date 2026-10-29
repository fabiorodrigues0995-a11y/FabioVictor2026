
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from check_links import load_urls, check_url


class TestCheckLinks(unittest.TestCase):

    def test_load_urls(self):
        with TemporaryDirectory() as directory:
            file_path = Path(directory) / "data.json"

            file_path.write_text(
                json.dumps([
                    {"name": "Site A", "url": "https://example.com"},
                    {"name": "Sem URL"},
                    {"name": "URL vazia", "url": " "}
                ]),
                encoding="utf-8",
            )

            urls = load_urls(file_path)

            self.assertEqual(len(urls), 1)
            self.assertEqual(urls[0]["name"], "Site A")
            self.assertEqual(
                urls[0]["url"], "https://example.com"
            )

    @patch("check_links.build_opener")
    def test_active_link(self, mock_build_opener):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response

        mock_build_opener.return_value.open.return_value = response

        status, detail = check_url("https://example.com")

        self.assertEqual(status, "ATIVO")
        self.assertEqual(detail, 200)

    @patch("check_links.build_opener")
    def test_redirect(self, mock_build_opener):
        mock_build_opener.return_value.open.side_effect = HTTPError(
            "https://example.com",
            301,
            "Moved Permanently",
            {},
            None,
        )

        status, detail = check_url("https://example.com")

        self.assertEqual(status, "REDIRECIONAMENTO")
        self.assertEqual(detail, 301)

    @patch("check_links.build_opener")
    def test_not_found(self, mock_build_opener):
        mock_build_opener.return_value.open.side_effect = HTTPError(
            "https://example.com",
            404,
            "Not Found",
            {},
            None,
        )

        status, detail = check_url("https://example.com")

        self.assertEqual(status, "FALHA HTTP")
        self.assertEqual(detail, 404)


if __name__ == "__main__":
    unittest.main()
