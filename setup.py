from setuptools import setup

setup(
    name='hakai_api',
    packages=['hakai_api'],
    version='0.3.0',
    description='Get Hakai database resources using http calls',
    author='Taylor Denouden',
    author_email='taylordenouden@gmail.com',
    url='https://github.com/tayden/hakai-api-client-python',
    download_url='https://github.com/tayden/hakai-api-client-python/archive/0.3.0.tar.gz',
    install_requires=[
        'future',
        'requests',
        'requests-oauthlib',
        'pytz',
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 2.7'
    ]
)
