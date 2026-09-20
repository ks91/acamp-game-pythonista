"""Run the app assigned to this iPad's TEAM_ID."""

import importlib

import config
from team_apps.registry import app_module_for_team


module = importlib.import_module(app_module_for_team(config.TEAM_ID))
module.run()
