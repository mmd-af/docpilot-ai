import unittest

from src.browsing import _html_to_text, build_live_prompt, validate_public_url
from src.rag import Citation, build_grounded_prompt, chunk_markdown


class RagTests(unittest.TestCase):
    def test_chunks_keep_heading_metadata(self):
        chunks = chunk_markdown("# Intro\nAlpha\n## Setup\nBeta", "docs/a.md", chunk_size=100, overlap=10)
        self.assertEqual([c["section"] for c in chunks], ["Intro", "Setup"])
        self.assertEqual(chunks[0]["source"], "docs/a.md")

    def test_prompt_contains_citation_context(self):
        prompt = build_grounded_prompt("How?", [Citation(
            title="a", section="Intro", source="docs/a.md",
            chunk_id="1", text="Use Workers."
        )])
        self.assertIn("docs/a.md", prompt)
        self.assertIn("Use Workers.", prompt)

    def test_live_prompt_contains_source_url(self):
        source = type("Source", (), {
            "url": "https://example.com/help",
            "content": "Apply before the permit expires.",
        })()
        prompt = build_live_prompt("What should I do?", [source])
        self.assertIn("https://example.com/help", prompt)
        self.assertIn("Apply before the permit expires.", prompt)

    def test_private_urls_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_public_url("http://127.0.0.1/admin")

    def test_public_urls_are_accepted(self):
        self.assertEqual(
            validate_public_url("https://workinromania.gov.ro/"),
            "https://workinromania.gov.ro/",
        )

    def test_html_fallback_removes_scripts_and_tags(self):
        self.assertEqual(
            _html_to_text("<h1>Hello</h1><script>ignore()</script><p>World</p>"),
            "Hello World",
        )


if __name__ == "__main__":
    unittest.main()
