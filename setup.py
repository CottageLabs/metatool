from setuptools import setup, find_packages

setup(
    name = 'gtr',
    version = '0.0.1',
    packages = find_packages(),
    install_requires = [
            "orcid-python",
            "lxml"
		]
)

