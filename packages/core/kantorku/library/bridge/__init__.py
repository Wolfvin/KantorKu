"""
Bridge — Integration layer between KantorKu office workers and the Library.

The bridge module provides two key components:

- **KantorKuLibraryBridge**: Connects KantorKu workers to the Library, enabling
  them to find solutions, save their work, and inject relevant context before
  executing tasks.
- **LosionExporter**: Exports Library data in Losion training formats (pretraining,
  RLHF QA, RLHF solutions, preference pairs) and generates fine-tuning data
  for the Librarian model.
"""

from kantorku.library.bridge.kantorku_bridge import KantorKuLibraryBridge
from kantorku.library.bridge.losion_exporter import LosionExporter

__all__ = ["KantorKuLibraryBridge", "LosionExporter"]
