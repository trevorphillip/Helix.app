# helix_apps/med_prep/app_api.py
from helix_platform.plugins import register

class MedPrepPlugin:
    slug = "medprep"                  # <-- must match exactly
    title = "Med-Prep (Bio & Chem)"
    version = "0.1.0"
    icon = None

    def get_viewmodel(self):
        # Minimal, safe defaults. Replace with your real logic later.
        return {
            "list_tracks": lambda: {"General": ["Intro"]},
            "next_due_cards": lambda user, track, module, limit=1: [],
            "grade_card": lambda user, card_id, correct: None,
        }

    def run_cli(self, **kwargs):
        return 0

register(MedPrepPlugin())
