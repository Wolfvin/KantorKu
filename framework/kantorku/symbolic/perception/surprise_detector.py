"""
SurpriseDetector — deteksi ketika input baru kontradiksi dengan
atom yang sudah aktif di working memory.

Dipakai untuk: menandai kontradiksi, trigger re-evaluation,
atau memberi sinyal ke Losion bahwa ada konflik struktural.
"""
from kantorku.symbolic.client.rsvs_client import RsvsClient
from kantorku.symbolic.perception.activation_state import ActivationState


class SurpriseDetector:
    """
    Cek apakah atom baru yang diaktifkan bertentangan dengan
    atom yang sudah ada di ActivationState.

    Untuk sekarang: deteksi sederhana via appraise() RSVS.
    Di masa depan: bisa pakai NeuroSymbolicVerifier dari Losion.
    """

    def __init__(self, rsvs: RsvsClient, activation_state: ActivationState,
                 surprise_threshold: float = 0.3):
        self.rsvs = rsvs
        self.state = activation_state
        self.surprise_threshold = surprise_threshold

    def check(self, text: str) -> list[dict]:
        """
        Return list of surprises — dict berisi {node_id, expected, got, severity}.
        Empty list jika tidak ada kejutan.
        """
        # Gunakan RSVS appraise untuk cek konsistensi struktural
        appraise_result = self.rsvs.appraise(text)

        surprises = []
        for item in appraise_result.items:
            if item.agree_pct < (1.0 - self.surprise_threshold):
                surprises.append({
                    "node_id": item.node_id,
                    "expected_agree": 1.0,
                    "got_agree": item.agree_pct,
                    "severity": 1.0 - item.agree_pct,
                    "text": text,
                })

        return surprises
