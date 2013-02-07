import os

from setuptools import setup, find_packages

requires = [
    'pyramid',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'waitress',
    'docutils',
    'gunicorn',
    'psycopg2',
    ]

setup(name='blog',
      version='0.0',
      description='blog',
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='blog',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = blog:main
      [console_scripts]
      initialize_blog_db = blog.scripts.initializedb:main
      """,
      )
