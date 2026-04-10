from django.test import TestCase
from django.contrib.auth.models import User
from pay_app.models import Cabinet, Tag, CabinetTag

class SearchFormTestCase(TestCase):
    def test_empty_get(self):
        response = self.client.get('/en/dev/search/', HTTP_HOST='docs.djangoproject.dev:8000')
        self.assertEqual(response.status_code, 400)


class CabinetTagModelTestCase(TestCase):
    def setUp(self):
        User.objects.create_user(username='admin', password='secret123')
        self.cabinet = Cabinet.objects.create(
            link='https://example.com',
            login='cab-login',
            password='cab-pass',
            email_login='cab@example.com',
            email_password='mail-pass',
            note='test cabinet',
        )
        self.tag = Tag.objects.create(name='Немає сервісів', slug='no-services')

    def test_can_assign_tag_to_cabinet(self):
        CabinetTag.objects.create(cabinet=self.cabinet, tag=self.tag)
        self.assertEqual(self.cabinet.cabinet_tags.count(), 1)
        self.assertEqual(self.cabinet.cabinet_tags.first().tag.name, 'Немає сервісів')