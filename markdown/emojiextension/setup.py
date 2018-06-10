from setuptools import setup, find_packages

setup(
    name='emojiextension',
    description='Extension for displaying Emojis',
    version='1.0',
    py_modules=['emojiextension'],
    install_requires = ['markdown>=2.5'],
    packages=find_packages(),
    package_data={'': ['*.json']},
    include_package_data=True
)