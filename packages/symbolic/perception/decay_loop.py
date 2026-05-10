"""
DecayLoop — background process yang menjalankan aktivasi decay.

Dijalankan sebagai asyncio task, bukan thread terpisah.
"""
import asyncio
from kantorku.symbolic.perception.activation_state import ActivationState


class DecayLoop:
    """
    Decay berjalan setiap tick_interval_seconds.

    Rekomendasi: 5 detik per tick untuk percakapan normal.
    Lebih lambat = atom bertahan lebih lama di working memory.
    """

    def __init__(self, state: ActivationState, tick_interval_seconds: float = 5.0):
        self.state = state
        self.tick_interval = tick_interval_seconds
        self._running = False

    async def start(self) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(self.tick_interval)
            self.state.decay()

    def stop(self) -> None:
        self._running = False
