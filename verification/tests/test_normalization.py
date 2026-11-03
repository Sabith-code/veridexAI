import unittest

from verification.simplicity_client import SimplicityAPIError, normalize_search_response


class NormalizeSearchResponseTests(unittest.TestCase):
    def test_normalizes_sources_without_reordering_them(self) -> None:
        result = normalize_search_response(
            {
                "message": "Alexander Graham Bell is commonly credited.",
                "sources": [
                    {
                        "content": "First source content",
                        "metadata": {"title": "First", "url": "https://first.example"},
                    },
                    {"content": "Second source content", "metadata": {"title": "Second"}},
                ],
            }
        ).to_dict()

        self.assertEqual(result["answer"], "Alexander Graham Bell is commonly credited.")
        self.assertEqual(
            result["sources"],
            [
                {"content": "First source content", "title": "First", "url": "https://first.example"},
                {"content": "Second source content", "title": "Second", "url": None},
            ],
        )

    def test_accepts_missing_metadata_as_null_title_and_url(self) -> None:
        result = normalize_search_response({"message": "Answer", "sources": [{"content": "Evidence"}]}).to_dict()
        self.assertEqual(result["sources"], [{"content": "Evidence", "title": None, "url": None}])

    def test_rejects_malformed_source_content(self) -> None:
        with self.assertRaisesRegex(SimplicityAPIError, "content"):
            normalize_search_response({"message": "Answer", "sources": [{"content": 42}]})

    def test_rejects_missing_sources_list(self) -> None:
        with self.assertRaisesRegex(SimplicityAPIError, "sources"):
            normalize_search_response({"message": "Answer"})
