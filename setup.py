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
    version=os.getenv('VERSION', 'latest'),
    license='MIT',
    description='Get Hakai database resources using http calls',
    long_description=open('README.md').read()
)
