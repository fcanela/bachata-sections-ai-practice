"""The reference: the label files of the site, read where the owner keeps them.

    fixtures/audio/dev/<song>/labels.json   the labels, never committed
    fixtures/audio/dev/<song>/mix.m4a       the recording they describe, never committed

fixtures/audio/README.md describes the format. problems() checks it:

- The song has a tempo, the time of the first beat (`lead_s`) and a number of beats, so
  beat n is at `lead_s + n * 60 / bpm`.
- The sections follow each other with no gap: each starts where the previous one ends,
  on a beat. Their beats add up to `total_beats`, and a section's blocks add up to the
  section.
- `structure` is the rhythm, as the site names it, or null.

scripts/measure_first_beat.py adds two fields. The labels' times are early by a constant
amount per song, so the first beat is measured on the audio:

- `first_beat_s`: where the first beat is in the mix.
- `mix_sha256`: the mix it was measured on. reference_beats() refuses any other mix.

What a check compares the analysis with:

- reference_beats(): the time of every labelled beat.
- reference_counts(): the count of every labelled beat, by the rules of ACCEPTANCE.md.
- beat_problems(), bar_problems() and count_matches(): how the detected beats, their
  places in the bar and their counts differ from those.
"""

import json
from pathlib import Path

DEV = Path(__file__).parent / "audio" / "dev"

# Two times are the same beat when they are this close, in seconds. It was 70 ms. It grew
# on 2026-10-05, as ACCEPTANCE.md allows up to 120 ms: on Old Town Road, from 108 to
# 114 s, the attacks of the mix sit 50 ms after the labels' grid, and three beats found
# there are 73, 76 and 84 ms from their label. Those figures hold for a first beat put at
# the start of the attack, as the script measures it. LOG.md, session 3, has the rest.
SAME_BEAT_S = 0.090

# Times in the label files are rounded to the millisecond.
ROUNDING_S = 0.0011


def labelled_songs():
    """The folders that have labels, by song name. Empty when the material is not on the machine."""
    return {path.parent.name: path.parent for path in sorted(DEV.glob("*/labels.json"))}


def read_labels(folder):
    return json.loads((folder / "labels.json").read_text())


def problems(labels):
    """What is wrong with a label file, one line per problem. Empty when it is valid."""
    found = []

    def number(value, least=0):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= least

    def count(value):
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    def text(value):
        return isinstance(value, str) and value.strip() != ""

    if not text(labels.get("title")):
        found.append("title: missing")
    if not (number(labels.get("bpm")) and labels["bpm"] > 0):
        found.append("bpm: must be a positive number")
    if not number(labels.get("lead_s")):
        found.append("lead_s: must be a number of seconds, 0 or more")
    if not count(labels.get("total_beats")):
        found.append("total_beats: must be a positive whole number")
    if not number(labels.get("total_s")):
        found.append("total_s: must be a number of seconds")
    sections = labels.get("sections")
    if not (isinstance(sections, list) and sections):
        found.append("sections: must be a non-empty list")
    if found:
        return found

    def time_of(beat):
        return labels["lead_s"] + beat * 60 / labels["bpm"]

    def spans(at, part, first_beat):
        """Checks one section or block. Returns its number of beats, or None."""
        if not (part.get("structure") is None or text(part.get("structure"))):
            found.append(f"{at}.structure: must be a rhythm name or null")
        if not count(part.get("beats")):
            found.append(f"{at}.beats: must be a positive whole number")
            return None
        for name, beat in (("start_s", first_beat), ("end_s", first_beat + part["beats"])):
            if not number(part.get(name)):
                found.append(f"{at}.{name}: must be a number of seconds")
            elif abs(part[name] - time_of(beat)) > ROUNDING_S:
                found.append(f"{at}.{name}: is {part[name]}, but beat {beat} is at {time_of(beat):.3f}")
        return part["beats"]

    beat = 0
    for i, section in enumerate(sections):
        at = f"sections[{i}]"
        if not text(section.get("title")):
            found.append(f"{at}.title: missing")
        beats = spans(at, section, beat)
        if beats is None:
            return found
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            found.append(f"{at}.blocks: must be a list")
        elif blocks:
            block_beat = beat
            for j, block in enumerate(blocks):
                block_beats = spans(f"{at}.blocks[{j}]", block, block_beat)
                if block_beats is None:
                    return found
                block_beat += block_beats
            if block_beat != beat + beats:
                found.append(f"{at}.blocks: add up to {block_beat - beat} beats, the section has {beats}")
        beat += beats

    if beat != labels["total_beats"]:
        found.append(f"sections: add up to {beat} beats, total_beats is {labels['total_beats']}")
    if abs(labels["total_s"] - time_of(labels["total_beats"])) > ROUNDING_S:
        found.append(f"total_s: is {labels['total_s']}, but the last section ends at {time_of(beat):.3f}")

    measured = "first_beat_s" in labels or "mix_sha256" in labels
    if measured and not number(labels.get("first_beat_s")):
        found.append("first_beat_s: must be a number of seconds")
    if measured and not (
        isinstance(labels.get("mix_sha256"), str)
        and len(labels["mix_sha256"]) == 64
        and set(labels["mix_sha256"]) <= set("0123456789abcdef")
    ):
        found.append("mix_sha256: must be 64 lowercase hex characters")
    return found


def reference_beats(labels, mix_sha256):
    """The time of every labelled beat in the mix with that sha256, in seconds."""
    if labels.get("mix_sha256") != mix_sha256:
        raise ValueError(
            "the first beat was not measured on this mix: run `uv run python scripts/measure_first_beat.py`"
        )
    return [labels["first_beat_s"] + n * 60 / labels["bpm"] for n in range(labels["total_beats"])]


def reference_counts(labels):
    """The count of every labelled beat, 1 to 8, by the rules of ACCEPTANCE.md, slice 2.

    The count starts again at every section and at every block. A section without blocks
    is whole ochos from its start, and what is left over is at its end: a half phrase,
    counted 1 to 4, is the last bar of its section.
    """
    counts = []
    for section in labels["sections"]:
        blocks = [block["beats"] for block in section["blocks"]] or [section["beats"]]
        for beats in blocks:
            counts += [beat % 8 + 1 for beat in range(beats)]
    return counts


def bar_problems(reference, counts, detected, bars):
    """Where the place of a beat in its bar differs from the reference, one line per beat.

    `counts` is the count of every labelled beat and `bars` the place in the bar of every
    detected one. A labelled beat with no detected beat is a problem here too.
    """
    found = []
    for time, count in zip(reference, counts):
        nearest = min(range(len(detected)), key=lambda n: abs(detected[n] - time))
        if abs(detected[nearest] - time) > SAME_BEAT_S:
            found.append(f"no beat at {time:.3f} s")
        elif bars[nearest] != (count - 1) % 4 + 1:
            found.append(f"the beat at {time:.3f} s is beat {bars[nearest]} of its bar, the labels say {(count - 1) % 4 + 1}")
    return found


def count_matches(reference, counts, detected, shown):
    """How many labelled beats are shown with the count of the reference."""
    matches = 0
    for time, count in zip(reference, counts):
        nearest = min(range(len(detected)), key=lambda n: abs(detected[n] - time))
        matches += abs(detected[nearest] - time) <= SAME_BEAT_S and shown[nearest] == count
    return matches


def beat_problems(reference, detected):
    """How the detected beats differ from the labelled ones, one line per problem.

    From the first labelled beat to the last, every labelled beat must have exactly one
    detected beat that is the same beat, and no detected beat may be without a labelled
    one. Beats detected before the first labelled beat or after the last are not judged.
    """
    found = []
    judged = [time for time in detected if reference[0] - SAME_BEAT_S <= time <= reference[-1] + SAME_BEAT_S]
    matches = [[] for _ in reference]
    for time in judged:
        nearest = min(range(len(reference)), key=lambda n: abs(reference[n] - time))
        if abs(reference[nearest] - time) <= SAME_BEAT_S:
            matches[nearest].append(time)
        else:
            found.append(
                f"detected beat at {time:.3f} s has no labelled beat: "
                f"the nearest is {abs(reference[nearest] - time) * 1000:.0f} ms away, at {reference[nearest]:.3f} s"
            )
    for time, same in zip(reference, matches):
        if not same:
            found.append(f"labelled beat at {time:.3f} s has no detected beat")
        elif len(same) > 1:
            found.append(f"labelled beat at {time:.3f} s has {len(same)} detected beats: {same}")
    return found
