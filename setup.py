from setuptools import setup

setup(
    name='hakai_api',
    packages=['hakai_api'],
    version='0.2.2',
    description='Get Hakai database resources using http calls',
    url='https://github.com/tayden/hakai-api-client-python',
    author='Taylor Denouden',
    author_email='taylor.denouden@hakai.org',
    license='MIT',
    install_requires=[
        'future',
        'pytz',
        'requests',
        'requests-oauthlib',
        'six',
    ],
    zip_safe=False,
)
