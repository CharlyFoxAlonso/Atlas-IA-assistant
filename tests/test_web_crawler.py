import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
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
            file_indexer = Mock(return_value=SimpleNamespace(
                status="indexed", chunk_count=3, error=None
            ))
            digester = Mock(return_value="resumen")
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=1, memory_root=str(root),
                session=session, resolver=resolver, llm=llm, digester=digester,
                reindexer=reindexer, file_indexer=file_indexer,
                respect_robots=False, request_delay=0,
            )
            events = list(crawler.crawl("https://example.com/"))
            self.assertEqual(crawler.request_count, 2)
            self.assertEqual(crawler.processed_count, 1)
            saved = list((root / "dest" / "tema_seguro").glob("article_*.md"))
            self.assertTrue(saved)
            file_indexer.assert_called_once_with(str(saved[0]))
            reindexer.assert_not_called()
            self.assertTrue(any(event["estado"] == "indexado" for event in events))
            self.assertEqual(events[-1]["guardadas"], 1)
            self.assertEqual(events[-1]["indexadas"], 1)
            self.assertTrue(events[-1]["reindexado"])
            self.assertEqual(events[-1]["estado_indice"], "actualizado")

    def test_selected_motor_and_model_are_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({"https://example.com/": FakeResponse(useful_html())})
            llm_mock = Mock(side_effect=llm)
            digester = Mock(return_value="resumen")
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root), session=session,
                resolver=resolver, llm=llm_mock, digester=digester,
                file_indexer=lambda _: SimpleNamespace(
                    status="indexed", chunk_count=1, error=None
                ), motor="groq", modelo="modelo-prueba",
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
                file_indexer=lambda _: SimpleNamespace(
                    status="indexed", chunk_count=1, error=None
                ), respect_robots=False, request_delay=0,
            )
            list(crawler.crawl("https://example.com/"))
            files = list((root / "dest" / "tema_seguro").glob("article_*.md"))
            self.assertEqual(len(files), 2)
            self.assertNotEqual(files[0].name, files[1].name)

    def test_multiple_pages_are_indexed_individually_without_full_rebuild(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(useful_html("/article")),
                "https://example.com/article": FakeResponse(useful_html()),
            })
            file_indexer = Mock(side_effect=[
                SimpleNamespace(status="indexed", chunk_count=2, error=None),
                SimpleNamespace(status="indexed", chunk_count=4, error=None),
            ])
            full_reindexer = Mock()
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=2, memory_root=str(root),
                session=session, resolver=resolver, llm=llm, digester=lambda **_: "ok",
                file_indexer=file_indexer, reindexer=full_reindexer,
                respect_robots=False, request_delay=0,
            )

            events = list(crawler.crawl("https://example.com/"))

            files = list((root / "dest" / "tema_seguro").glob("*.md"))
            self.assertEqual(len(files), 2)
            self.assertEqual(file_indexer.call_count, 2)
            self.assertEqual(
                {call.args[0] for call in file_indexer.call_args_list},
                {str(path) for path in files},
            )
            full_reindexer.assert_not_called()
            summary = events[-1]
            self.assertEqual(summary["guardadas"], 2)
            self.assertEqual(summary["indexadas"], 2)
            self.assertEqual(summary["fallidas_indexacion"], 0)
            self.assertEqual(summary["estado_indice"], "actualizado")
            self.assertTrue(summary["reindexado"])

    def test_skipped_page_is_not_saved_or_indexed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file_indexer = Mock()
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root),
                session=FakeSession({"https://example.com/": FakeResponse(short_html())}),
                resolver=resolver, llm=llm, digester=lambda **_: "ok",
                file_indexer=file_indexer, respect_robots=False, request_delay=0,
            )

            events = list(crawler.crawl("https://example.com/"))

            self.assertFalse(list((root / "dest").rglob("*.md")))
            file_indexer.assert_not_called()
            self.assertEqual(events[-1]["omitidas"], 1)
            self.assertEqual(events[-1]["indexadas"], 0)
            self.assertEqual(events[-1]["estado_indice"], "sin_cambios")
            self.assertFalse(events[-1]["reindexado"])

    def test_failed_index_result_keeps_markdown_and_reports_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crawler = WebCrawler(
                str(root / "dest"), "tema", memory_root=str(root),
                session=FakeSession({"https://example.com/": FakeResponse(useful_html())}),
                resolver=resolver, llm=llm, digester=lambda **_: "ok",
                file_indexer=Mock(return_value=SimpleNamespace(
                    status="failed", chunk_count=0, error="Chroma caído"
                )), respect_robots=False, request_delay=0,
            )

            events = list(crawler.crawl("https://example.com/"))

            self.assertEqual(len(list((root / "dest").rglob("*.md"))), 1)
            self.assertTrue(any(event["estado"] == "advertencia" for event in events))
            summary = events[-1]
            self.assertEqual(summary["guardadas"], 1)
            self.assertEqual(summary["indexadas"], 0)
            self.assertEqual(summary["fallidas_indexacion"], 1)
            self.assertEqual(summary["estado_indice"], "sin_cambios")
            self.assertFalse(summary["reindexado"])
            self.assertIn("RAG sin cambios", summary["mensaje"])

    def test_indexer_exception_does_not_stop_later_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session = FakeSession({
                "https://example.com/": FakeResponse(useful_html("/article")),
                "https://example.com/article": FakeResponse(useful_html()),
            })
            file_indexer = Mock(side_effect=[
                RuntimeError("backend no disponible"),
                SimpleNamespace(status="indexed", chunk_count=2, error=None),
            ])
            crawler = WebCrawler(
                str(root / "dest"), "tema", max_pages=2, memory_root=str(root),
                session=session, resolver=resolver, llm=llm, digester=lambda **_: "ok",
                file_indexer=file_indexer, respect_robots=False, request_delay=0,
            )

            events = list(crawler.crawl("https://example.com/"))

            self.assertEqual(len(list((root / "dest").rglob("*.md"))), 2)
            self.assertEqual(file_indexer.call_count, 2)
            self.assertTrue(any(event["estado"] == "advertencia" for event in events))
            summary = events[-1]
            self.assertEqual(summary["guardadas"], 2)
            self.assertEqual(summary["indexadas"], 1)
            self.assertEqual(summary["fallidas_indexacion"], 1)
            self.assertEqual(summary["estado_indice"], "parcial")
            self.assertTrue(summary["reindexado"])
            self.assertIn("parcialmente", summary["mensaje"])

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
