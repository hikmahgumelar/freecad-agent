# Watchdog Auto-Restart Test

Validation marker for GitHub auto-sync and Supervisor autorestart.

Expected behavior: watchdog detects this commit, pulls it with `git pull --ff-only`, exits normally, and Supervisor starts a new watchdog process automatically.
