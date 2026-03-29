from setuptools import setup, find_packages

setup(
    name="cpp-recomdatation-system",
    version="1.0.0",
    description=(
        "AI-powered competitive programming recommendation and analytics system "
        "integrating Codeforces and LeetCode"
    ),
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "click>=8.1.0",
        "tabulate>=0.9.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cprec=main:cli",
        ],
    },
)
