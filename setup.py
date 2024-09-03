from setuptools import setup, find_packages

with open('README', encoding='utf-8') as readme:
    readme = readme.read()

with open('LICENSE', encoding='utf-8') as lic:
    lic = lic.read()

setup(
    name='ToolBox',
    version='0.1.0',
    description='Easy-to-download toolbox.',
    long_description=readme,
    author='RedbeanW',
    author_email='redbeana44945@gmail.com',
    url='https://github.com/',
    license=license,
    packages=find_packages(),
)
