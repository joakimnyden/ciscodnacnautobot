from os import path
from setuptools import setup, find_packages


with open("requirements.txt") as f:
    requirements = f.read().splitlines()
with open(
    path.join(path.abspath(path.dirname(__file__)), "README.md"), encoding="utf-8"
) as f:
    long_description = f.read()

PACKAGE_KEYWORDS = [
    "cisco",
    "dna",
    "dnacenter",
    "python",
    "api",
    "sdk",
    "Nautobot",
]

setup(
    name="ciscodnacnautbot",
    version="1.0.0",
    description="Cisco DNA Center Integration with Nautobot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/joakimnyden/ciscodnacnautobot.git",
    author="Robert Csapo",
    author_email="rcsapo@cisco.com",
    maintainer="Joakim Nydén",
    maintainer_email="joakim.nyden@cygate.se",
    license="CISCO SAMPLE CODE LICENSE",
    install_requires=requirements,
    packages=find_packages(exclude=["img"]),
    package_data={"ciscodnacnautobot": ["templates/*/*.html"]},
    include_package_data=True,
    python_requires=">=3.3",
    zip_safe=False,
)
