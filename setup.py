from setuptools import setup

setup(name='hakai_api',
      version='0.1',
      description='Get Hakai database resources with http calls',
      url='https://github.com/tayden/hakai-api-client-python',
      author='Taylor Denouden',
      author_email='taylor.denouden@hakai.org',
      license='MIT',
      packages=['hakai_api'],
      install_requires=[
          'requests',
          'requests-oauthlib',
      ],
      zip_safe=False)
