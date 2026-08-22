"""The single human touch in the pipeline: a post-PASS physical-safety gate.

Runs the verifier one final time, prints the full report, and asks a person to confirm
before the controller would ever be treated as cleared to fly near a real aircraft.

This gate is deliberately placed AFTER verification. No human is involved in writing,
testing, or fixing the controller. A drone operating near a live jet engine is a
physical-safety decision, and that is the only thing a person signs here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller import Controller  # noqa: E402
from sim.run_verifier import verify  # noqa: E402


def main():
    ok, results = verify(Controller, count=30, base_seed=1000, verbose=True)

    if not ok:
        print("Verification FAILED. Nothing to approve.")
        sys.exit(1)

    print("Verification PASSED across all scenarios.")
    print("Artifact: controller.py, written entirely by Devin with no human edits.\n")
    print("This is the only human decision in the pipeline.")
    print("Approving means: cleared for inspection flight near a real aircraft.\n")

    answer = input("Approve for real-aircraft inspection flight? [yes/no] ").strip().lower()
    if answer == "yes":
        print("\nAPPROVED. Controller released for flight operations.")
        sys.exit(0)
    print("\nNOT APPROVED. Controller held.")
    sys.exit(1)


if __name__ == "__main__":
    main()
