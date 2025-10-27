from pathlib import Path

from setuptools import find_packages, setup

ROOT = Path(__file__).parent
README = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").stat().st_size else ""

setup(
    name="bkdetect",
    version="0.2.1",
    description="Инструмент поиска источников текста и совпадающих фрагментов.",
    long_description=README,
    long_description_content_type="text/markdown" if README else None,
    author="bk_detect maintainers",
    py_modules=["bkDetetct", "documents", "loaders", 
                "text_pipeline", "indexing", "source_finder"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "beautifulsoup4",
        "nltk",
        "scipy",
        "scikit-learn",
        "python-docx",
    ],
    entry_points={
        "console_scripts": [
            "bk-detect=bkDetetct:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Source": "https://github.com/your-org/bk_detect",
    },
)
