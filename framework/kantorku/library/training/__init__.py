"""
Training — Fine-tuning recipe and data formatting for the Librarian model.

This module provides tools for preparing and generating training data for
the Losion Librarian model:

- **LibrarianRecipe**: Fine-tuning hyperparameters and configuration, with
  YAML serialization/deserialization support.
- **DataFormatter**: Formats Library entries into various training data
  representations (pretraining, RLHF, preference pairs).
- **generate_finetune_data**: CLI script for generating Librarian fine-tuning
  data from the Library archive.
"""

__all__: list[str] = []
