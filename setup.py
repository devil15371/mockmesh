# /Users/aman/mockmesh/setup.py
import os
from setuptools import setup, find_packages

setup(
    name="mockmesh",
    version="0.2.0",
    author="Aman Kumar",
    description="An in-process, schema-driven, zero-dependency AWS auto-mocking engine for Python developers",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/amankumar/mockmesh",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
    ],
    python_requires=">=3.8",
    install_requires=[
        "botocore>=1.0.0",
        "boto3>=1.0.0",
    ],
    entry_points={
        'console_scripts': [
            'mockmesh=mockmesh.server:main',
        ],
    },
)
