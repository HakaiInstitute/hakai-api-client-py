from setuptools import setup

setup(name='hakai_api',
      version='0.2.0',
      description='Get Hakai database resources with http calls',
      url='https://github.com/tayden/hakai-api-client-python',
      author='Taylor Denouden',
      author_email='taylor.denouden@hakai.org',
      license='MIT',
      packages=['hakai_api'],
      install_requires=[
          'future',
          'pytz',
          'requests',
          'requests-oauthlib',
          'six',
      ],
      zip_safe=False)
