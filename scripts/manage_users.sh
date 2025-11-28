#!/bin/bash
# User Management Shell Script
#
# Admin CLI for managing users in the Firestore-based tier system.
#
# Commands:
#     add <email> <tier>     - Add a new user with specified tier
#     update <email> <tier>  - Update existing user's tier
#     list                   - List all users
#     list --tier <tier>     - List users by tier
#     remove <email>         - Remove a user
#     migrate-env            - Migrate from ALLOWED_USERS env var
#
# Usage:
#     ./scripts/manage_users.sh add user@example.com premium
#     ./scripts/manage_users.sh update user@example.com regular
#     ./scripts/manage_users.sh list
#     ./scripts/manage_users.sh list --tier premium
#     ./scripts/manage_users.sh remove user@example.com
#     ./scripts/manage_users.sh migrate-env

set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtual environment if it exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Set PYTHONPATH to include project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run the Python script with all arguments
python "$SCRIPT_DIR/manage_users.py" "$@"
