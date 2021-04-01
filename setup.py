import os

from setuptools import setup

setup(
    name='hakai_api',
    packages=['hakai_api'],
    version=os.environ['VERSION'],
    description='Get Hakai database resources using http calls',
    url='https://github.com/tayden/hakai-api-client-python',
    author='Taylor Denouden',
    author_email='taylor.denouden@hakai.org',
    license='MIT',
    install_requires=[
        'pytz',
        'requests',
        'requests-oauthlib',
    ],
    zip_safe=False,
)
