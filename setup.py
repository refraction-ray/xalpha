import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="xalpha",
    version="0.1.2",
    author="refraction-ray",
    author_email="refraction-ray@protonmail.com",
    description="all about fund investment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/refraction-ray/xalpha",
    packages=setuptools.find_packages(),
    install_requires=[
        'ply==3.4',
        'lxml',
        'slimit>=0.8.1',
        'pandas',
        'scipy',
        'requests',
        'pyecharts==0.5.5',
        'beautifulsoup4',
        'sqlalchemy'],
    tests_require=['pytest'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
