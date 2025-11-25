#!/usr/bin/env python3
"""
Reset User Limits Script
Usage: python scripts/reset_limits.py [user_id] [--daily] [--concurrent] [--all-limits]

If user_id is provided, resets limits for that user.
If not provided, lists users with active sessions and prompts for action.

Options:
  --daily       Reset daily session limits only
  --concurrent  Reset concurrent session limits only
  --all-limits  Reset both daily and concurrent limits (default if no option specified)
"""
import os
import sys
import argparse
from google.cloud import firestore

# Add app directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings

settings = get_settings()

def get_db():
    print(f"Connecting to Firestore project: {settings.gcp_project_id}")
    return firestore.Client(
        project=settings.gcp_project_id,
        database=settings.firestore_database
    )

def reset_user(db, user_id, reset_daily=True, reset_concurrent=True):
    print(f"Resetting limits for user: {user_id}")
    doc_ref = db.collection(settings.firestore_user_limits_collection).document(user_id)

    try:
        doc = doc_ref.get()
        if not doc.exists:
            print(f"User document {user_id} not found.")
            return

        updates = {}

        # Reset concurrent sessions
        if reset_concurrent:
            updates["concurrent_sessions"] = {
                "count": 0,
                "active_session_ids": []
            }
            print(f"  - Reset concurrent sessions for {user_id}")

        # Reset daily sessions
        if reset_daily:
            updates["daily_sessions"] = {
                "count": 0,
                "reset_time": None
            }
            print(f"  - Reset daily sessions for {user_id}")

        if updates:
            doc_ref.update(updates)
            print(f"Successfully reset limits for {user_id}")
        
    except Exception as e:
        print(f"Error resetting user {user_id}: {e}")

def get_user_email(db, user_id):
    """Look up user email from sessions collection."""
    from google.cloud.firestore_v1.base_query import FieldFilter
    sessions = db.collection(settings.firestore_sessions_collection)
    # Find any session with this user_id to get their email
    query = sessions.where(filter=FieldFilter("user_id", "==", user_id)).limit(1)
    for session in query.stream():
        data = session.to_dict()
        return data.get("user_email", "")
    return ""

def list_and_prompt(db, reset_daily=True, reset_concurrent=True):
    collection = db.collection(settings.firestore_user_limits_collection)
    docs = collection.stream()

    users_with_limits = []
    user_emails = {}
    print("\nUsers with session limits:")
    print("-" * 90)
    print(f"{'Email':<35} | {'User ID':<30} | {'Concurrent':<10} | {'Daily':<8}")
    print("-" * 90)

    for doc in docs:
        data = doc.to_dict()
        concurrent = data.get("concurrent_sessions", {})
        daily = data.get("daily_sessions", {})

        active_count = concurrent.get("count", 0)
        daily_count = daily.get("count", 0)

        # Show users with any non-zero limits
        if active_count > 0 or daily_count > 0:
            users_with_limits.append(doc.id)
            email = get_user_email(db, doc.id)
            user_emails[doc.id] = email
            email_display = email[:33] + ".." if len(email) > 35 else email
            user_id_display = doc.id[:28] + ".." if len(doc.id) > 30 else doc.id
            print(f"{email_display:<35} | {user_id_display:<30} | {active_count:<10} | {daily_count:<8}")

    if not users_with_limits:
        print("No users found with active limits.")
        return

    print("-" * 60)
    reset_type = []
    if reset_daily:
        reset_type.append("daily")
    if reset_concurrent:
        reset_type.append("concurrent")
    print(f"Will reset: {', '.join(reset_type)} limits")

    choice = input("\nEnter User ID to reset, 'all' to reset all listed, or 'q' to quit: ").strip()

    if choice.lower() == 'q':
        return
    elif choice.lower() == 'all':
        for uid in users_with_limits:
            reset_user(db, uid, reset_daily, reset_concurrent)
    else:
        if choice in users_with_limits:
            reset_user(db, choice, reset_daily, reset_concurrent)
        else:
            print("User ID not in list.")
            if input("Try to reset anyway? (y/n): ").lower() == 'y':
                reset_user(db, choice, reset_daily, reset_concurrent)

def main():
    parser = argparse.ArgumentParser(description="Reset Improv Olympics User Limits")
    parser.add_argument("user_id", nargs="?", help="User ID to reset")
    parser.add_argument("--daily", action="store_true", help="Reset daily session limits only")
    parser.add_argument("--concurrent", action="store_true", help="Reset concurrent session limits only")
    parser.add_argument("--all-limits", action="store_true", help="Reset both daily and concurrent limits")
    args = parser.parse_args()

    # Determine what to reset
    # If no flags specified, reset both (default behavior)
    if not args.daily and not args.concurrent and not args.all_limits:
        reset_daily = True
        reset_concurrent = True
    else:
        reset_daily = args.daily or args.all_limits
        reset_concurrent = args.concurrent or args.all_limits

    try:
        db = get_db()
        if args.user_id:
            reset_user(db, args.user_id, reset_daily, reset_concurrent)
        else:
            list_and_prompt(db, reset_daily, reset_concurrent)
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have Google Cloud credentials set up:")
        print("  gcloud auth application-default login")

if __name__ == "__main__":
    main()
