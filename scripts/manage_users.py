#!/usr/bin/env python3
"""User Management CLI Script

Admin CLI for managing users in the Firestore-based tier system.

Commands:
    add <email> <tier>     - Add a new user with specified tier
    update <email> <tier>  - Update existing user's tier
    list                   - List all users
    list --tier <tier>     - List users by tier
    remove <email>         - Remove a user
    migrate-env            - Migrate from ALLOWED_USERS env var

Usage:
    python scripts/manage_users.py add user@example.com premium
    python scripts/manage_users.py update user@example.com regular
    python scripts/manage_users.py list
    python scripts/manage_users.py list --tier premium
    python scripts/manage_users.py remove user@example.com
    python scripts/manage_users.py migrate-env
"""

import asyncio
import sys
import argparse
import os
from typing import Optional

# Add project root to path dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)


async def add_user(email: str, tier: str, created_by: str = "cli-admin") -> None:
    """Add a new user."""
    from app.services.user_service import create_user, UserAlreadyExistsError
    from app.models.user import UserTier

    try:
        tier_enum = UserTier(tier.lower())
    except ValueError:
        print(f"Error: Invalid tier '{tier}'. Must be one of: free, regular, premium")
        sys.exit(1)

    try:
        user = await create_user(
            email=email,
            tier=tier_enum,
            created_by=created_by,
        )
        print(f"✅ User added successfully:")
        print(f"   Email: {user.email}")
        print(f"   Tier: {user.tier.value}")
        print(f"   Created: {user.created_at}")
    except UserAlreadyExistsError:
        print(f"Error: User with email {email} already exists")
        sys.exit(1)
    except Exception as e:
        print(f"Error adding user: {e}")
        sys.exit(1)


async def update_user(email: str, tier: str) -> None:
    """Update user's tier."""
    from app.services.user_service import update_user_tier, UserNotFoundError
    from app.models.user import UserTier

    try:
        tier_enum = UserTier(tier.lower())
    except ValueError:
        print(f"Error: Invalid tier '{tier}'. Must be one of: free, regular, premium")
        sys.exit(1)

    try:
        success = await update_user_tier(email, tier_enum)
        if success:
            print(f"✅ User tier updated successfully:")
            print(f"   Email: {email}")
            print(f"   New Tier: {tier_enum.value}")
        else:
            print(f"Error: Failed to update user tier")
            sys.exit(1)
    except UserNotFoundError:
        print(f"Error: User with email {email} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error updating user: {e}")
        sys.exit(1)


async def list_users(tier: Optional[str] = None) -> None:
    """List users, optionally filtered by tier."""
    from app.services.user_service import list_users as svc_list_users
    from app.models.user import UserTier

    tier_filter = None
    if tier:
        try:
            tier_filter = UserTier(tier.lower())
        except ValueError:
            print(f"Error: Invalid tier '{tier}'. Must be one of: free, regular, premium")
            sys.exit(1)

    try:
        users = await svc_list_users(tier=tier_filter)

        if not users:
            if tier_filter:
                print(f"No users found with tier: {tier_filter.value}")
            else:
                print("No users found")
            return

        print(f"{'Email':<40} {'Tier':<10} {'Created':<20} {'Last Login':<20}")
        print("-" * 90)

        for user in users:
            created = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "N/A"
            last_login = user.last_login_at.strftime("%Y-%m-%d %H:%M") if user.last_login_at else "Never"
            print(f"{user.email:<40} {user.tier.value:<10} {created:<20} {last_login:<20}")

        print("-" * 90)
        print(f"Total: {len(users)} users")

    except Exception as e:
        print(f"Error listing users: {e}")
        sys.exit(1)


async def remove_user(email: str) -> None:
    """Remove a user."""
    from app.services.user_service import delete_user, UserNotFoundError

    try:
        success = await delete_user(email)
        if success:
            print(f"✅ User removed successfully: {email}")
        else:
            print(f"Error: Failed to remove user")
            sys.exit(1)
    except UserNotFoundError:
        print(f"Error: User with email {email} not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error removing user: {e}")
        sys.exit(1)


async def migrate_from_env(default_tier: str = "regular") -> None:
    """Migrate users from ALLOWED_USERS environment variable."""
    from app.services.user_service import migrate_from_allowed_users
    from app.models.user import UserTier
    from app.config import get_settings

    settings = get_settings()

    if not settings.allowed_users_list:
        print("No users found in ALLOWED_USERS environment variable")
        return

    try:
        tier_enum = UserTier(default_tier.lower())
    except ValueError:
        print(f"Error: Invalid tier '{default_tier}'. Must be one of: free, regular, premium")
        sys.exit(1)

    print(f"Migrating {len(settings.allowed_users_list)} users from ALLOWED_USERS...")
    print(f"Default tier: {tier_enum.value}")
    print()

    for email in settings.allowed_users_list:
        print(f"  - {email}")

    print()

    try:
        result = await migrate_from_allowed_users(
            default_tier=tier_enum,
            created_by="migration-script",
        )

        print("Migration complete:")
        print(f"  ✅ Migrated: {result['migrated']}")
        print(f"  ⏭️  Skipped (already exists): {result['skipped']}")
        if result.get('errors', 0) > 0:
            print(f"  ❌ Errors: {result['errors']}")

    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="User Management CLI for Firestore-based tier system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s add user@example.com premium
  %(prog)s update user@example.com regular
  %(prog)s list
  %(prog)s list --tier premium
  %(prog)s remove user@example.com
  %(prog)s migrate-env
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new user")
    add_parser.add_argument("email", help="User email address")
    add_parser.add_argument("tier", choices=["free", "regular", "premium"], help="User tier")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update user tier")
    update_parser.add_argument("email", help="User email address")
    update_parser.add_argument("tier", choices=["free", "regular", "premium"], help="New tier")

    # List command
    list_parser = subparsers.add_parser("list", help="List users")
    list_parser.add_argument("--tier", choices=["free", "regular", "premium"], help="Filter by tier")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a user")
    remove_parser.add_argument("email", help="User email address")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate-env", help="Migrate from ALLOWED_USERS env var")
    migrate_parser.add_argument(
        "--tier",
        default="regular",
        choices=["free", "regular", "premium"],
        help="Default tier for migrated users (default: regular)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run the appropriate command
    if args.command == "add":
        asyncio.run(add_user(args.email, args.tier))
    elif args.command == "update":
        asyncio.run(update_user(args.email, args.tier))
    elif args.command == "list":
        asyncio.run(list_users(args.tier))
    elif args.command == "remove":
        asyncio.run(remove_user(args.email))
    elif args.command == "migrate-env":
        asyncio.run(migrate_from_env(args.tier))


if __name__ == "__main__":
    main()
