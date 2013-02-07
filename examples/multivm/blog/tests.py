import unittest
import transaction

from pyramid import testing

from .models import DBSession


class TestMyView(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            Page,
            )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        with transaction.manager:
            page = Page(name='TestPage', data='testing 123')
            DBSession.add(page)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_it(self):
        from .views import view_page
        request = testing.DummyRequest(path='/TestPage', matchdict={'pagename': 'TestPage'})
        info = view_page(request)
        self.assertEqual(info['page'].name, 'TestPage')
        self.assertEqual(info['page'].data, 'testing 123')
