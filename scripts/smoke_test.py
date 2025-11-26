#!/usr/bin/env python3
"""
Smoke Test Script for Improv Olympics Production Deployment

This script validates core functionality after deployment.
It performs quick, non-invasive tests to ensure the service is operational.

Usage:
    python smoke_test.py --url https://your-service-url.run.app
    python smoke_test.py --url https://your-service-url.run.app --verbose
    python smoke_test.py --url http://localhost:8080
"""

import sys
import argparse
import requests
from typing import Optional
from datetime import datetime
import json


class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


class SmokeTest:
    def __init__(self, base_url: str, verbose: bool = False, skip_auth: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.skip_auth = skip_auth
        self.session_id: Optional[str] = None
        self.test_results = []

    def log(self, message: str, level: str = "info"):
        if level == "success":
            print(f"{Color.GREEN}\u2713{Color.END} {message}")
        elif level == "error":
            print(f"{Color.RED}\u2717{Color.END} {message}")
        elif level == "warning":
            print(f"{Color.YELLOW}!{Color.END} {message}")
        elif level == "info":
            print(f"{Color.BLUE}>{Color.END} {message}")
        else:
            print(message)

    def verbose_log(self, message: str):
        if self.verbose:
            print(f"  {message}")

    def record_result(self, test_name: str, passed: bool, message: str = ""):
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })

    def test_health(self) -> bool:
        try:
            self.log("Testing health endpoint...", "info")
            response = requests.get(f"{self.base_url}/health", timeout=10)

            self.verbose_log(f"Status: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:200]}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log("Health check passed", "success")
                    self.record_result("health_check", True)
                    return True

            self.log(f"Health check failed: status {response.status_code}", "error")
            self.record_result("health_check", False, f"Status: {response.status_code}")
            return False

        except Exception as e:
            self.log(f"Health check failed: {str(e)}", "error")
            self.record_result("health_check", False, str(e))
            return False

    def test_ready(self) -> bool:
        try:
            self.log("Testing readiness endpoint...", "info")
            response = requests.get(f"{self.base_url}/ready", timeout=10)

            self.verbose_log(f"Status: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:200]}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ready":
                    self.log("Readiness check passed", "success")
                    self.record_result("readiness_check", True)
                    return True

            self.log(f"Readiness check failed: status {response.status_code}", "error")
            self.record_result("readiness_check", False, f"Status: {response.status_code}")
            return False

        except Exception as e:
            self.log(f"Readiness check failed: {str(e)}", "error")
            self.record_result("readiness_check", False, str(e))
            return False

    def test_create_session(self) -> bool:
        if self.skip_auth:
            self.log("Skipping session creation (requires auth)", "warning")
            self.record_result("session_creation", None, "Skipped (auth required)")
            return True

        try:
            self.log("Testing session creation...", "info")

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Authenticated-User-Id": "smoke-test-user",
                "X-Goog-Authenticated-User-Email": "smoke-test@example.com"
            }

            payload = {
                "location": "Smoke Test Arena",
                "user_name": "Smoke Test User"
            }

            response = requests.post(
                f"{self.base_url}/api/v1/session/start",
                json=payload,
                headers=headers,
                timeout=30
            )

            self.verbose_log(f"Status: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:500]}")

            if response.status_code == 201:
                data = response.json()
                self.session_id = data.get("session_id")

                if self.session_id and data.get("status") == "initialized":
                    self.log("Session creation passed", "success")
                    self.verbose_log(f"Session ID: {self.session_id}")
                    self.record_result("session_creation", True, f"Session: {self.session_id}")
                    return True

            self.log(f"Session creation failed: status {response.status_code}", "error")
            self.record_result("session_creation", False, f"Status: {response.status_code}")
            return False

        except Exception as e:
            self.log(f"Session creation failed: {str(e)}", "error")
            self.record_result("session_creation", False, str(e))
            return False

    def test_execute_turn(self) -> bool:
        if self.skip_auth or not self.session_id:
            self.log("Skipping turn execution (requires session)", "warning")
            self.record_result("turn_execution", None, "Skipped (requires session)")
            return True

        try:
            self.log("Testing turn execution...", "info")

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Authenticated-User-Id": "smoke-test-user",
                "X-Goog-Authenticated-User-Email": "smoke-test@example.com"
            }

            payload = {
                "user_input": "Hello! This is a smoke test for our improv scene.",
                "turn_number": 1
            }

            response = requests.post(
                f"{self.base_url}/api/v1/session/{self.session_id}/turn",
                json=payload,
                headers=headers,
                timeout=60
            )

            self.verbose_log(f"Status: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:500]}")

            if response.status_code == 200:
                data = response.json()

                if (data.get("partner_response") and
                    data.get("room_vibe") and
                    data.get("turn_number") == 1):

                    self.log("Turn execution passed", "success")
                    self.verbose_log(f"Partner: {data['partner_response'][:100]}...")
                    self.record_result("turn_execution", True)
                    return True

            self.log(f"Turn execution failed: status {response.status_code}", "error")
            self.record_result("turn_execution", False, f"Status: {response.status_code}")
            return False

        except Exception as e:
            self.log(f"Turn execution failed: {str(e)}", "error")
            self.record_result("turn_execution", False, str(e))
            return False

    def test_close_session(self) -> bool:
        if self.skip_auth or not self.session_id:
            self.log("Skipping session closure (no session)", "warning")
            self.record_result("session_closure", None, "Skipped (no session)")
            return True

        try:
            self.log("Testing session closure...", "info")

            headers = {
                "X-Goog-Authenticated-User-Id": "smoke-test-user",
                "X-Goog-Authenticated-User-Email": "smoke-test@example.com"
            }

            response = requests.post(
                f"{self.base_url}/api/v1/session/{self.session_id}/close",
                headers=headers,
                timeout=10
            )

            self.verbose_log(f"Status: {response.status_code}")
            self.verbose_log(f"Response: {response.text[:200]}")

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "closed":
                    self.log("Session closure passed", "success")
                    self.record_result("session_closure", True)
                    return True

            self.log(f"Session closure failed: status {response.status_code}", "error")
            self.record_result("session_closure", False, f"Status: {response.status_code}")
            return False

        except Exception as e:
            self.log(f"Session closure failed: {str(e)}", "error")
            self.record_result("session_closure", False, str(e))
            return False

    def run_all_tests(self) -> bool:
        print(f"\n{Color.BLUE}{'='*60}{Color.END}")
        print(f"{Color.BLUE}Improv Olympics Smoke Test Suite{Color.END}")
        print(f"{Color.BLUE}URL: {self.base_url}{Color.END}")
        print(f"{Color.BLUE}Time: {datetime.now().isoformat()}{Color.END}")
        print(f"{Color.BLUE}{'='*60}{Color.END}\n")

        results = [
            self.test_health(),
            self.test_ready(),
            self.test_create_session(),
            self.test_execute_turn(),
            self.test_close_session()
        ]

        print(f"\n{Color.BLUE}{'='*60}{Color.END}")
        print(f"{Color.BLUE}Test Results Summary{Color.END}")
        print(f"{Color.BLUE}{'='*60}{Color.END}\n")

        passed_count = sum(1 for r in self.test_results if r["passed"] is True)
        failed_count = sum(1 for r in self.test_results if r["passed"] is False)
        skipped_count = sum(1 for r in self.test_results if r["passed"] is None)

        for result in self.test_results:
            status_icon = "✓" if result["passed"] is True else ("✗" if result["passed"] is False else "⊘")
            color = Color.GREEN if result["passed"] is True else (Color.RED if result["passed"] is False else Color.YELLOW)
            print(f"{color}{status_icon}{Color.END} {result['test']}: {result['message'] if result['message'] else 'OK'}")

        print(f"\n{Color.BLUE}Total:{Color.END} {len(self.test_results)} tests")
        print(f"{Color.GREEN}Passed:{Color.END} {passed_count}")
        print(f"{Color.RED}Failed:{Color.END} {failed_count}")
        print(f"{Color.YELLOW}Skipped:{Color.END} {skipped_count}")

        all_passed = all(r is True or r is None for r in results)

        if all_passed:
            print(f"\n{Color.GREEN}{'='*60}{Color.END}")
            print(f"{Color.GREEN}All smoke tests passed!{Color.END}")
            print(f"{Color.GREEN}{'='*60}{Color.END}\n")
        else:
            print(f"\n{Color.RED}{'='*60}{Color.END}")
            print(f"{Color.RED}Some smoke tests failed!{Color.END}")
            print(f"{Color.RED}{'='*60}{Color.END}\n")

        return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test suite for Improv Olympics deployment"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of the service (e.g., https://your-service.run.app)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="Skip tests requiring authentication"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    smoke_test = SmokeTest(
        base_url=args.url,
        verbose=args.verbose,
        skip_auth=args.skip_auth
    )

    success = smoke_test.run_all_tests()

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "base_url": args.url,
            "success": success,
            "results": smoke_test.test_results
        }
        print(json.dumps(output, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
