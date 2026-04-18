# stim_games package — subprograms that run on the T-Rex Talker
#
# Each stim game is a Python module with either:
#   1. A top-level `run(machine)` function, OR
#   2. A class that subclasses `Subprogram` and is exposed as `GAME = MyGame`
#
# The host Machine launches them via `subprogram_runner.launch_subprogram()`.
