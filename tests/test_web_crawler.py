import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.web_crawler import CrawlerSecurityError, WebCrawler, validate_public_url


PUBLIC_IP = "93.184.216.34"


def resolver(hostname):
    if hostname in {"localhost", "127.0.0.1", "internal.test"}:
        return ["127.0.0.1"]
    return [PUBLIC_IP]


class FakeResponse:
    def __init__(self, body="", status=200, headers=None, encoding="utf-8"):
        self.body = body.encode(encoding) if isinstance(body, str) else body
        self.status_code = status
        self.headers = {"Content-Type": "text/html", **(headers or {})}
        self.encoding = encoding
        self.closed = False

    def iter_content(self, chunk_size=65536):
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset:offset + chunk_size]

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.get(url)
        if response is None:
            return FakeResponse("not found", status=404)
        return response() if callable(response) else response


def useful_html(*links):
    anchors = "".join(f'<a href="{link}">link</a>' for link in links)
    words = " ".join(f"contenidoimportante{i}" for i in range(55))
    return f"<html><body>{anchors}<main>{words}</main></body></html>"


def short_html(*links):
    anchors = "".join(f'<a href="{link}">link</a>' for link in links)
    return f"<html><body>{anchors}<p>índice breve</p></body></html>"


def llm(prompt, **kwargs):
    return "tema_seguro" if "nombre corto" in prompt else "SI"


class WebCrawlerSecurityTests(unittest.TestCase):
    def test_private_and_local_urls_are_rejected(self):
        for url in ("http://127.0.0.1/admin", "http://localhost/", "file:///etc/passwd"):
            with self.subTest(url=url), self.assertRaises(CrawlerSecurityError):
                validate_public_url(url, resolver=resolver)

    def test_embedded_credentials_are_rejected(self):
        with self.assertRaises(CrawlerSecurityError):
            validate_public_url("https://user:password@example.com/", resolver=resolver)

    def test_destination_outside_memory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(CrawlerSecurityError):
                WebCrawler(
                    root_folder=str(root.parent),
                    memory_root=str(root),
                    theme="test",
                    resolver=resolver,
                )

    def test_redirect_to_private_host_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(
                    status=302, headers={"Location": "http://127.0.0.1/private"}
                )
            })
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root), session=session,
                resolver=resolver, llm=llm, digester=lambda **_: "ok",
                respect_robots=False, request_delay=0,
            )
            events = list(crawler.crawl("https://example.com/"))
            self.assertTrue(any(event["estado"] == "error" for event in events))
            self.assertEqual(len(session.calls), 1)
            self.assertEqual(crawler.processed_count, 0)

    def test_large_response_is_rejected_before_processing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(
                    "small", headers={"Content-Length": "999999"}
                )
            })
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root), session=session,
                resolver=resolver, llm=llm, digester=lambda **_: "ok",
                max_response_bytes=2048, respect_robots=False, request_delay=0,
            )
            events = list(crawler.crawl("https://example.com/"))
            self.assertTrue(any("tamaño" in event["mensaje"] for event in events if event["estado"] == "error"))
            self.assertFalse((root / "dest").exists())


class WebCrawlerBehaviorTests(unittest.TestCase):
    def test_irrelevant_index_still_discovers_relevant_child(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(short_html("/article")),
                "https://example.com/article": FakeResponse(useful_html()),
            })
            reindexer = Mock()
            digester = Mock(return_value="resumen")
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=1, memory_root=str(root),
                session=session, resolver=resolver, llm=llm, digester=digester,
                reindexer=reindexer, respect_robots=False, request_delay=0,
            )
            events = list(crawler.crawl("https://example.com/"))
            self.assertEqual(crawler.request_count, 2)
            self.assertEqual(crawler.processed_count, 1)
            self.assertTrue(list((root / "dest" / "tema_seguro").glob("article_*.md")))
            reindexer.assert_called_once_with()
            self.assertTrue(events[-1]["reindexado"])

    def test_selected_motor_and_model_are_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({"https://example.com/": FakeResponse(useful_html())})
            llm_mock = Mock(side_effect=llm)
            digester = Mock(return_value="resumen")
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root), session=session,
                resolver=resolver, llm=llm_mock, digester=digester,
                reindexer=lambda: None, motor="groq", modelo="modelo-prueba",
                respect_robots=False, request_delay=0,
            )
            list(crawler.crawl("https://example.com/"))
            self.assertTrue(all(call.kwargs["motor"] == "groq" for call in llm_mock.call_args_list))
            self.assertTrue(all(call.kwargs["modelo_groq"] == "modelo-prueba" for call in llm_mock.call_args_list))
            self.assertEqual(digester.call_args.kwargs["motor"], "groq")
            self.assertEqual(digester.call_args.kwargs["modelo"], "modelo-prueba")

    def test_request_limit_is_independent_from_saved_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(short_html("/a", "/b", "/c")),
                "https://example.com/a": FakeResponse(short_html()),
                "https://example.com/b": FakeResponse(short_html()),
                "https://example.com/c": FakeResponse(short_html()),
            })
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=10, max_requests=2,
                memory_root=str(root), session=session, resolver=resolver, llm=llm,
                digester=lambda **_: "ok", respect_robots=False, request_delay=0,
            )
            events = list(crawler.crawl("https://example.com/"))
            self.assertEqual(crawler.request_count, 2)
            self.assertEqual(len(session.calls), 2)
            self.assertEqual(events[-1]["solicitudes"], 2)

    def test_query_variants_get_distinct_hashed_names(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(short_html("/article?page=1", "/article?page=2")),
                "https://example.com/article?page=1": FakeResponse(useful_html()),
                "https://example.com/article?page=2": FakeResponse(useful_html()),
            })
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=2, memory_root=str(root),
                session=session, resolver=resolver, llm=llm, digester=lambda **_: "ok",
                reindexer=lambda: None, respect_robots=False, request_delay=0,
            )
            list(crawler.crawl("https://example.com/"))
            files = list((root / "dest" / "tema_seguro").glob("article_*.md"))
            self.assertEqual(len(files), 2)
            self.assertNotEqual(files[0].name, files[1].name)

    def test_external_links_are_not_queued(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(short_html("https://other.example/page")),
            })
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root), session=session,
                resolver=resolver, llm=llm, digester=lambda **_: "ok",
                respect_robots=False, request_delay=0,
            )
            list(crawler.crawl("https://example.com/"))
            self.assertEqual(len(session.calls), 1)


if __name__ == "__main__":
    unittest.main()
