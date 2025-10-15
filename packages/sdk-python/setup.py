from setuptools import setup, find_packages

setup(
    name="ecosystem-sdk",
    version="0.1.0",
    description="Modularity SDK for Python",
    author="Modularity Contributors",
    packages=find_packages(),
    install_requires=[
        "Flask>=3.0.0",
        "flask-cors>=4.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "flake8>=7.0.0",
            "black>=23.12.1",
        ]
    },
    python_requires=">=3.8",
)
