"""
sofer — Publish any dataset to Hugging Face Hub with built-in validation.

Each dataset is described by a TOML file. The library validates the data
locally, generates the dataset package (Parquet, Dataset Card, LICENSE,
codebooks) with ``prepare``, and delivers it with ``publish`` — either to
the Hugging Face Hub or to a local directory.

Usage:
    sofer init my-dataset          # Create a TOML template
    sofer scan my-dataset.toml     # Auto-discover and register data files
    sofer prepare my-dataset.toml  # Generate the package locally (build/)
    sofer publish my-dataset.toml  # Deliver to Hugging Face or a local dir
    sofer validate my-dataset.toml # Check data integrity
    sofer codebook data.csv        # Generate a markdown codebook
"""

__version__ = "0.1.0"
