from django.test import TestCase

class SearchFormTestCase(TestCase):
    def test_empty_get(self):
        response = self.client.get('/en/dev/search/', HTTP_HOST='docs.djangoproject.dev:8000')
        self.assertEqual(response.status_code, 400)