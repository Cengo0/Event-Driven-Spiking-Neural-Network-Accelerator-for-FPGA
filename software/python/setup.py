"""Setup script for SpikePress.

Author: Jiwoon Lee (@metr0jw)
Organization: Kwangwoon University, Seoul, South Korea
Contact: jwlee@linux.com
"""

from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).resolve().parents[2]

setup(
    name="spikepress",
    version="0.1.0",
    author="Jiwoon Lee",
    author_email="metr0jw@example.com",
    description="SpikePress compiler API for SpikeMold-EDNP",
    long_description=(ROOT / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/metr0jw/Event-Driven-Spiking-Neural-Network-Accelerator-for-FPGA",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.13",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
        ],
        "pynq": [
            "pynq>=2.7.0",
        ],
    },
)
