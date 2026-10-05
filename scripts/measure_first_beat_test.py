import numpy as np

from scripts.measure_first_beat import RATE, best_shift


def test_the_shift_found_is_where_the_attacks_start():
    # Bursts of noise that die away in 40 ms, one per beat at 124 BPM, each starting
    # 83 ms after its label says. A quieter burst sits on every off-beat.
    labels = {"lead_s": 0.5, "bpm": 124, "total_beats": 60}
    random = np.random.default_rng(1)
    signal = random.normal(0, 0.001, RATE * 32)
    burst = random.normal(0, 1, 4000) * np.exp(-np.arange(4000) / 400)
    for n in range(120):
        start = round((0.5 + 0.083 + n * 30 / 124) * RATE)
        signal[start : start + 4000] += burst * (1.0 if n % 2 == 0 else 0.4)
    assert abs(best_shift(signal, labels) - 0.083) <= 0.002
