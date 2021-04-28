import os

from setuptools import setup

setup(
    name='hakai_api',
    url='https://github.com/HakaiInstitute/hakai-api-client-python',
    author='Taylor Denouden',
    author_email='taylor.denouden@hakai.org',
    packages=['hakai_api'],
    install_requires=[
        'pytz',
        'requests',
        'requests-oauthlib',
    ],
    version=os.getenv('VERSION', '1.0.0.dev1'),
    license='MIT',
    description='Get Hakai database resources using http calls',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown"
)
