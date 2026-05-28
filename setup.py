
# NOTE : Before build, if dependencies have changed,
#        requirements.txt should also be updated.
#        You can use "pipenv lock -r > requirements.txt"
#        or "pipenv requirements > requirements.txt".
#        Then, please delete the line starting with "-i".

# NOTE : To build, use `py setup.py sdist`

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

VERSION = "1.0.0"

setup(
    name='requester',
    license="MIT License",
    version=VERSION,
    description='Requesting system for NUCOSen',
    url='https://github.com/nucosen/requester-bot',
    author='Sitting-cat',
    author_email='info@koaku.ma',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.10, <4',
    install_requires=open(
        "requirements.txt",
        encoding="utf-8"
    ).read().splitlines(),
    entry_points={
        'console_scripts': [
            'requester=requester.cli:execute'
        ]
    },
    project_urls={
        'Bug Reports': 'https://github.com/nucosen/requester-bot/issues',
        'Source': 'https://github.com/nucosen/requester-bot',
    },
)
