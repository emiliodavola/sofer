"""
sofer — Publish any dataset to Hugging Face Hub with built-in validation.

Each dataset is described by a TOML file. The library validates the data locally,
generates codebooks, and uploads everything to HF following data-sharing best practices.

Usage:
    sofer init my-dataset          # Create a TOML template
    sofer scan my-dataset.toml     # Auto-discover and register data files
    sofer validate my-dataset.toml # Check data integrity
    sofer upload   my-dataset.toml # Upload to Hugging Face
    sofer codebook data.csv        # Generate a markdown codebook
"""

__version__ = "0.1.0"
