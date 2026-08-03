"""
data-uploader — Publish any dataset to Hugging Face Hub with built-in validation.

Each dataset is described by a TOML file. The library validates the data locally,
generates codebooks, and uploads everything to HF following data-sharing best practices.

Usage:
    data-uploader init my-dataset          # Create a TOML template
    data-uploader scan my-dataset.toml     # Auto-discover and register data files
    data-uploader validate my-dataset.toml # Check data integrity
    data-uploader upload   my-dataset.toml # Upload to Hugging Face
    data-uploader codebook data.csv        # Generate a markdown codebook
"""

__version__ = "0.1.0"
