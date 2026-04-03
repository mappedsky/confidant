# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from setuptools import find_packages
from setuptools import setup

with open("VERSION") as f:
    VERSION = f.read()

setup(
    name="confidant",
    version=VERSION,
    packages=find_packages(exclude=["test*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "Flask",
        "blinker",
        "botocore",
        "boto3",
        "cryptography",
        "cffi",
        "Flask-Session",
        "redis",
        "types-redis",
        "Flask-SSLify",
        "requests",
        "PyJWT[crypto]",
        "ndg-httpsclient",
        "pyasn1",
        "pyOpenSSL",
        "guard",
        "PyYAML",
        "types-PyYAML",
        "gunicorn",
        "gevent",
        "greenlet",
        "statsd",
        "pydantic",
        "lru-dict",
        "python-json-logger",
        "pytest",
        "pytest-mock",
        "pytest-cov",
        "pytest-lazy-fixture",
        "pytest-env",
        "pytest-gevent",
        "pytz",
        "types-pytz",
        "cerberus",
        "mypy",
    ],
    author="Ryan Lane",
    author_email="rlane@ryandlane.com",
    description="A secret management system and client.",
    license="apache2",
    url="https://github.com/mappedsky/confidant",
    entry_points={
        "console_scripts": [
            "confidant-admin = confidant.scripts.manage:main",
        ]
    },
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
