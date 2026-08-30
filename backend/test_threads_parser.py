import unittest
from unittest.mock import patch

from main import extract_post_text_from_html, normalize_threads_url


class ThreadsParserTests(unittest.TestCase):
    def test_extract_post_text_uses_ocr_when_og_data_is_generic(self):
        html = """
        <html><head>
            <meta property="og:title" content="shopink247 Threads Post">
            <meta property="og:description" content="🙌">
            <meta property="og:image" content="https://example.com/catalog-1.jpg">
            <meta property="og:image" content="https://example.com/catalog-2.jpg">
        </head></html>
        """

        with patch('main.ocr_image_text', return_value='Eggs RM7.50\nWhole chicken RM12.90\nGiant Setapak sale'):
            text, image_urls = extract_post_text_from_html(html, 'https://www.threads.com/share/BAVhRUmY1E/')

        self.assertIn('Eggs', text)
        self.assertIn('Whole chicken', text)
        self.assertIn('Giant Setapak', text)
        self.assertEqual(image_urls, ['https://example.com/catalog-1.jpg', 'https://example.com/catalog-2.jpg'])

    def test_normalize_threads_share_url_uses_canonical_post_url(self):
        with patch('main.requests.get') as mock_get:
            mock_get.return_value.text = '''<html><head><link rel="canonical" href="https://www.threads.com/@shopink247/post/abc123" /></head></html>'''
            mock_get.return_value.url = 'https://www.threads.com/share/BAVhRUmY1E/'
            mock_get.return_value.raise_for_status.return_value = None

            normalized = normalize_threads_url('https://www.threads.com/share/BAVhRUmY1E/')

        self.assertEqual(normalized, 'https://www.threads.com/@shopink247/post/abc123')


if __name__ == '__main__':
    unittest.main()
