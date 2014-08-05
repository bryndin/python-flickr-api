from setuptools import setup
import re

VERSION_FILE = "tornado_flickr_api/_version.py"
try:
    vers_content = open(VERSION_FILE, "r").read()
    version_str = re.search(r'__version__ = "(.+?)"', vers_content).group(1)
except:
    raise RuntimeError("Could not read version file.")

setup(
    name="tornado_flickr_api",
    version=version_str,
    description="Async Python wrapper for the Flickr API based on Tornado framework",
    author="Dmitriy Bryndin",
    author_email="bryndin@gmail.com",
    url="https://github.com/bryndin/tornado-flickr-api",
    packages=["tornado_flickr_api"],
    install_requires=[
        "oauth",
        "tornado",
    ],
    license="BSD License",
)
