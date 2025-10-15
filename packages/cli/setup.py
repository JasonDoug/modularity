from setuptools import setup, find_packages

setup(
    name="ecosystem-cli",
    version="0.1.0",
    description="CLI tool for Modularity",
    author="Modularity Contributors",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "rich>=13.7.0",
        "requests>=2.31.0",
        "pyyaml>=6.0.1",
    ],
    entry_points={
        "console_scripts": [
            "ecosystem=ecosystem_cli:cli",
        ],
    },
    python_requires=">=3.8",
)
