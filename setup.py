import setuptools
import os
import shutil

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

## super ugly but quick way to exclude .py files in the packages

excludes = ["holdings.py"]

for f in excludes:
    absf = os.path.join(os.getcwd(), "xalpha", f)
    if os.path.exists(absf):
        shutil.move(absf, os.path.join(os.getcwd(), "xalpha", f + ".keep"))

setuptools.setup(
    name="xalpha",
    version="0.12.1",
    author="refraction-ray",
    author_email="znfesnpbh@gmail.com",
    description="all about fund investment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/refraction-ray/xalpha",
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        "lxml",
        "pandas<2.0",
        "xlrd>=1.0.0",  #  read excel support
        "numpy==1.26.4",
        "scipy",
        "matplotlib",
        "requests",
        "pyecharts==1.7.1;python_version<='3.9'",  # broken api between 0.x and 1.x
        "pyecharts==1.9.1;python_version>'3.9'",
        "beautifulsoup4>=4.9.0",
        "sqlalchemy<2.0",
        "pysocks",  # sock5 proxy support
    ],
    tests_require=["pytest"],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)


for f in excludes:
    absf = os.path.join(os.getcwd(), "xalpha", f + ".keep")
    if os.path.exists(absf):
        shutil.move(absf, os.path.join(os.getcwd(), "xalpha", f))
