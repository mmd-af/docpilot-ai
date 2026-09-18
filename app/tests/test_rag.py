import unittest

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


if __name__ == "__main__":
    unittest.main()
