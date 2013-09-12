from setuptools import setup, find_packages

setup(
    name = 'gtr',
    version = '0.0.1',
    packages = find_packages(),
    install_requires = [
            "Flask==0.8",
            "Flask-Login",
            "Flask-WTF",
            "requests==1.1.0",
            "orcid-python",
            "lxml",
            "catflap",
            "python-Levenshtein",
            "python-dateutil"
		]
)

