"""Custom skip members logic for Sphinx AutoAPI documentation generation.

This module provides functions to determine which members should be skipped
or kept during API documentation generation, using centralized rules from
the include_exclude module.
"""

ignore_regex = [
    # No tests
    "*/test_*.py",
    # None of the render modules
    "*/render.py",
]

skip_dict: dict[str, list[str]] = {
    "package": [
        "pooltool.ani",
        "pooltool.ai",
        "pooltool.config",
        "pooltool.serialize",
        "pooltool.utils",
        # API: pooltool.evolution
        "pooltool.evolution.event_based",
        # API: pooltool.objects
        "pooltool.objects.ball",
        "pooltool.objects.cue",
        "pooltool.objects.table",
        # API: pooltool.ruleset
        "pooltool.ruleset.snooker",
        # API: pooltool.physics
        "pooltool.physics.evolve",
        "pooltool.physics.resolve",
    ],
    "module": [
        "pooltool.error",
        "pooltool.constants",
        "pooltool.main",
        # API: pooltool.evolution
        "pooltool.evolution.continuous",
        # API: pooltool.events
        "pooltool.events.datatypes",
        "pooltool.events.filter",
        "pooltool.events.utils",
        "pooltool.events.factory",
        # API: pooltool.objects
        "pooltool.objects.datatypes",
        # API: pooltool.ruleset
        "pooltool.ruleset.datatypes",
        "pooltool.ruleset.eight_ball",
        "pooltool.ruleset.nine_ball",
        "pooltool.ruleset.sandbox",
        "pooltool.ruleset.sum_to_three",
        "pooltool.ruleset.three_cushion",
        "pooltool.ruleset.utils",
        # API: pooltool.system
        "pooltool.system.datatypes",
        # API: pooltool.game
        "pooltool.game.datatypes",
        # API: pooltool.physics
        "pooltool.physics.engine",
        # API: pooltool.physics.resolve
        "pooltool.physics.resolve.models",
        "pooltool.physics.resolve.resolver",
    ],
    "function": [],
    "class": [],
    "attribute": [],
    "method": [],
    "property": [],
    "exception": [],
    "data": [
        "pooltool.system.multisystem",
    ],
}

# Overrides
keep_dict: dict[str, list[str]] = {
    "package": [],
    "module": [],
    "function": [],
    "class": [
        "Game",  # from pooltool.ani.animate
    ],
    "attribute": [],
    "method": [],
    "property": [],
    "exception": [],
    "data": [],
}

