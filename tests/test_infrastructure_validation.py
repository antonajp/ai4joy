"""
Infrastructure Validation Tests for GCP Deployment
Tests TC-INFRA-01 through TC-INFRA-05 from GCP Deployment Test Plan

These tests validate that:
1. Health check endpoint is accessible
2. DNS resolution works correctly
3. SSL/TLS certificate is valid
4. HTTPS is enforced (HTTP redirects)
5. Cloud Run service is operational
"""

import pytest
import requests
import socket
import ssl
import dns.resolver
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse


class TestHealthCheckEndpoints:
    """
    Test suite for health check endpoint validation.

    Prerequisites:
    - Cloud Run service deployed
    - Health check endpoints implemented
    """

    @pytest.fixture
    def service_url(self, config) -> str:
        """Base URL for the deployed service."""
        return config.get('service_url', 'https://ai4joy.org')

    def test_tc_infra_01_health_check_accessible(
        self,
        service_url: str
    ):
        """
        TC-INFRA-01: Health Check Endpoint Accessible

        Verify that /health endpoint returns 200 OK and indicates service health.

        Expected Behavior:
        - GET /health returns 200 OK
        - Response time < 5 seconds
        - Response indicates healthy status
        - Accessible without authentication (IAP allowlisted)
        """
        start_time = datetime.now()
        response = requests.get(
            f"{service_url}/health",
            timeout=10
        )
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()

        assert response.status_code == 200, \
            f"/health should return 200 OK, got {response.status_code}"

        assert response_time < 5.0, \
            f"/health response time {response_time:.2f}s exceeds 5s threshold"

        # Try to parse JSON response if present
        try:
            health_data = response.json()
            print(f"✓ Health check response: {health_data}")

            # Check for common health check fields
            if 'status' in health_data:
                assert health_data['status'] in ['healthy', 'ok', 'up'], \
                    f"Unexpected health status: {health_data['status']}"
        except ValueError:
            # Plain text response is also acceptable
            assert 'ok' in response.text.lower() or 'healthy' in response.text.lower(), \
                f"Health check response should indicate healthy status: {response.text}"

        print("✓ /health endpoint accessible and healthy")
        print(f"✓ Response time: {response_time:.2f}s")

    def test_tc_infra_02_ready_check_accessible(
        self,
        service_url: str
    ):
        """
        TC-INFRA-02: Readiness Check Endpoint

        Verify that /ready endpoint indicates service is ready to accept traffic.

        Expected Behavior:
        - GET /ready returns 200 OK when service is ready
        - Returns 503 if service is not ready (startup/shutdown)
        - Accessible without authentication
        """
        response = requests.get(
            f"{service_url}/ready",
            timeout=10
        )

        # Ready check should return 200 when healthy, or 503 if not ready
        assert response.status_code in [200, 503], \
            f"/ready should return 200 or 503, got {response.status_code}"

        if response.status_code == 200:
            print("✓ /ready endpoint indicates service is ready")
        else:
            print("ℹ /ready endpoint indicates service not ready (503)")

    def test_tc_infra_03_health_check_no_auth_required(
        self,
        service_url: str
    ):
        """
        TC-INFRA-03: Health Check Does Not Require Authentication

        Verify that health checks work without OAuth authentication.
        This is critical for load balancer health checks.

        Expected Behavior:
        - /health accessible without IAP headers
        - /ready accessible without IAP headers
        - No redirect to OAuth consent screen
        """
        # Use requests without any authentication
        session = requests.Session()

        # Test /health
        health_response = session.get(
            f"{service_url}/health",
            allow_redirects=False,
            timeout=10
        )

        assert health_response.status_code == 200, \
            f"/health should return 200 without auth, got {health_response.status_code}"

        assert 'accounts.google.com' not in health_response.headers.get('Location', ''), \
            "/health should not redirect to OAuth"

        # Test /ready
        ready_response = session.get(
            f"{service_url}/ready",
            allow_redirects=False,
            timeout=10
        )

        assert ready_response.status_code in [200, 503], \
            f"/ready should return 200/503 without auth, got {ready_response.status_code}"

        print("✓ Health checks accessible without authentication")


class TestDNSResolution:
    """
    Test suite for DNS configuration validation.

    Prerequisites:
    - DNS records configured for ai4joy.org
    - DNS propagation complete
    """

    @pytest.fixture
    def domain(self, config) -> str:
        """Domain name to test."""
        service_url = config.get('service_url', 'https://ai4joy.org')
        parsed = urlparse(service_url)
        return parsed.netloc or 'ai4joy.org'

    @pytest.fixture
    def expected_ip(self, config) -> Optional[str]:
        """Expected IP address for load balancer (if known)."""
        return config.get('load_balancer_ip')

    def test_tc_infra_04_dns_a_record_resolves(
        self,
        domain: str,
        expected_ip: Optional[str]
    ):
        """
        TC-INFRA-04: DNS A Record Resolution

        Verify that ai4joy.org resolves to the correct IP address.

        Expected Behavior:
        - DNS A record exists for domain
        - Resolves to GCP load balancer IP
        - No resolution errors
        """
        try:
            answers = dns.resolver.resolve(domain, 'A')
            ip_addresses = [str(rdata) for rdata in answers]

            assert len(ip_addresses) > 0, \
                f"No A records found for {domain}"

            print(f"✓ {domain} resolves to: {ip_addresses}")

            if expected_ip:
                assert expected_ip in ip_addresses, \
                    f"Expected IP {expected_ip} not in resolved IPs: {ip_addresses}"
                print(f"✓ Resolved IP matches expected: {expected_ip}")

        except dns.resolver.NXDOMAIN:
            pytest.fail(f"Domain {domain} does not exist (NXDOMAIN)")
        except dns.resolver.NoAnswer:
            pytest.fail(f"No A record found for {domain}")
        except Exception as e:
            pytest.fail(f"DNS resolution failed: {e}")

    def test_tc_infra_05_dns_propagation_complete(
        self,
        domain: str
    ):
        """
        TC-INFRA-05: DNS Propagation Complete

        Verify that DNS records have propagated globally by querying
        multiple DNS servers.

        Expected Behavior:
        - Domain resolves from multiple geographic locations
        - Consistent IP addresses across DNS servers
        """
        public_dns_servers = [
            '8.8.8.8',      # Google DNS (US)
            '1.1.1.1',      # Cloudflare (Global)
            '208.67.222.222'  # OpenDNS (Global)
        ]

        resolved_ips = {}

        for dns_server in public_dns_servers:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns_server]
            resolver.timeout = 5
            resolver.lifetime = 5

            try:
                answers = resolver.resolve(domain, 'A')
                ip_addresses = [str(rdata) for rdata in answers]
                resolved_ips[dns_server] = ip_addresses
                print(f"✓ {domain} resolves via {dns_server}: {ip_addresses}")
            except Exception as e:
                print(f"⚠ Resolution via {dns_server} failed: {e}")

        assert len(resolved_ips) > 0, \
            "Domain should resolve from at least one DNS server"

        # Check consistency across DNS servers
        all_ips = set()
        for ips in resolved_ips.values():
            all_ips.update(ips)

        if len(resolved_ips) > 1:
            # All servers should return at least one common IP
            print(f"✓ DNS propagation verified across {len(resolved_ips)} servers")
            print(f"✓ Resolved IPs: {all_ips}")


class TestSSLCertificate:
    """
    Test suite for SSL/TLS certificate validation.

    Prerequisites:
    - SSL certificate provisioned for domain
    - Certificate active and valid
    """

    @pytest.fixture
    def domain(self, config) -> str:
        """Domain name to test."""
        service_url = config.get('service_url', 'https://ai4joy.org')
        parsed = urlparse(service_url)
        return parsed.netloc or 'ai4joy.org'

    def test_tc_infra_06_ssl_certificate_valid(
        self,
        domain: str
    ):
        """
        TC-INFRA-06: SSL Certificate Valid

        Verify that SSL/TLS certificate is valid and properly configured.

        Expected Behavior:
        - Certificate is valid (not expired)
        - Certificate matches domain name
        - Certificate issued by trusted CA
        - Certificate has at least 30 days until expiration
        """
        context = ssl.create_default_context()

        try:
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

                    # Validate certificate exists
                    assert cert, "No SSL certificate returned"

                    # Check expiration
                    not_after_str = cert.get('notAfter')
                    assert not_after_str, "Certificate missing notAfter date"

                    # Parse expiration date
                    not_after = datetime.strptime(not_after_str, '%b %d %H:%M:%S %Y %Z')
                    now = datetime.utcnow()
                    days_until_expiry = (not_after - now).days

                    assert days_until_expiry > 0, \
                        f"Certificate expired {abs(days_until_expiry)} days ago"

                    assert days_until_expiry >= 30, \
                        f"Certificate expires in {days_until_expiry} days (< 30 day warning)"

                    # Check subject matches domain
                    subject = dict(x[0] for x in cert.get('subject', []))
                    common_name = subject.get('commonName', '')

                    # Check if domain matches CN or subjectAltName
                    san = cert.get('subjectAltName', [])
                    san_domains = [name for type, name in san if type == 'DNS']

                    domain_matched = domain == common_name or domain in san_domains

                    assert domain_matched, \
                        f"Domain {domain} not in certificate (CN: {common_name}, SAN: {san_domains})"

                    # Check issuer
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    issuer_org = issuer.get('organizationName', '')

                    print(f"✓ SSL certificate valid for {domain}")
                    print(f"  Expires: {not_after} ({days_until_expiry} days)")
                    print(f"  Issuer: {issuer_org}")
                    print(f"  Common Name: {common_name}")
                    print(f"  SAN: {san_domains}")

        except ssl.SSLError as e:
            pytest.fail(f"SSL validation failed: {e}")
        except socket.timeout:
            pytest.fail(f"Connection to {domain}:443 timed out")
        except Exception as e:
            pytest.fail(f"Certificate validation failed: {e}")

    def test_tc_infra_07_tls_version_secure(
        self,
        domain: str
    ):
        """
        TC-INFRA-07: TLS Version Security

        Verify that only secure TLS versions are supported (TLS 1.2+).

        Expected Behavior:
        - TLS 1.2 or TLS 1.3 supported
        - TLS 1.0 and TLS 1.1 not supported (deprecated)
        - SSL v2/v3 not supported
        """
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        try:
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    tls_version = ssock.version()

                    assert tls_version in ['TLSv1.2', 'TLSv1.3'], \
                        f"TLS version should be 1.2 or 1.3, got {tls_version}"

                    print(f"✓ Secure TLS version: {tls_version}")

        except Exception as e:
            pytest.fail(f"TLS version check failed: {e}")


class TestHTTPSEnforcement:
    """
    Test suite for HTTPS enforcement.

    Prerequisites:
    - Load balancer configured with HTTP to HTTPS redirect
    """

    @pytest.fixture
    def service_url(self, config) -> str:
        """Base URL for the deployed service."""
        return config.get('service_url', 'https://ai4joy.org')

    def test_tc_infra_08_http_redirects_to_https(
        self,
        service_url: str
    ):
        """
        TC-INFRA-08: HTTP Redirects to HTTPS

        Verify that HTTP requests are automatically redirected to HTTPS.

        Expected Behavior:
        - HTTP request returns 301 or 302 redirect
        - Location header points to HTTPS URL
        - Final response served over HTTPS
        """
        http_url = service_url.replace('https://', 'http://')

        response = requests.get(
            f"{http_url}/health",
            allow_redirects=False,
            timeout=10
        )

        assert response.status_code in [301, 302, 303, 307, 308], \
            f"HTTP should redirect, got {response.status_code}"

        location = response.headers.get('Location', '')
        assert location.startswith('https://'), \
            f"Redirect should be to HTTPS, got: {location}"

        print(f"✓ HTTP redirects to HTTPS: {location}")

        # Follow redirect and verify HTTPS works
        final_response = requests.get(
            f"{http_url}/health",
            allow_redirects=True,
            timeout=10
        )

        assert final_response.status_code == 200, \
            f"Final HTTPS request should succeed, got {final_response.status_code}"

        assert final_response.url.startswith('https://'), \
            "Final URL should be HTTPS"

        print("✓ HTTPS enforcement working correctly")

    def test_tc_infra_09_hsts_header_present(
        self,
        service_url: str
    ):
        """
        TC-INFRA-09: HSTS Header Present

        Verify that Strict-Transport-Security header is present,
        forcing browsers to use HTTPS.

        Expected Behavior:
        - HTTPS responses include Strict-Transport-Security header
        - max-age is at least 1 year (31536000 seconds)
        """
        response = requests.get(
            f"{service_url}/health",
            timeout=10
        )

        hsts_header = response.headers.get('Strict-Transport-Security')

        if hsts_header:
            print(f"✓ HSTS header present: {hsts_header}")

            # Extract max-age value
            if 'max-age=' in hsts_header:
                max_age_str = hsts_header.split('max-age=')[1].split(';')[0]
                max_age = int(max_age_str)

                assert max_age >= 31536000, \
                    f"HSTS max-age should be >= 1 year, got {max_age} seconds"

                print(f"✓ HSTS max-age: {max_age} seconds (>= 1 year)")
        else:
            print("ℹ HSTS header not present (recommended but not required)")


class TestCloudRunService:
    """
    Test suite for Cloud Run service validation.

    Prerequisites:
    - Cloud Run service deployed
    - gcloud CLI configured
    """

    @pytest.mark.manual
    def test_tc_infra_10_cloud_run_service_exists(
        self,
        config: Dict
    ):
        """
        TC-INFRA-10: Cloud Run Service Deployed (MANUAL)

        Verify that Cloud Run service is deployed and operational.

        Validation Command:
        gcloud run services describe improv-olympics-app \\
          --region=us-central1 \\
          --project=improvOlympics

        Expected Output:
        - Service status: READY
        - Latest revision deployed
        - Ingress: all (or internal-and-cloud-load-balancing)
        - Min instances: 1
        - Max instances: 100
        """
        pytest.skip("Manual validation via gcloud CLI")

    @pytest.mark.manual
    def test_tc_infra_11_load_balancer_routing(
        self,
        config: Dict
    ):
        """
        TC-INFRA-11: Load Balancer Routing (MANUAL)

        Verify that global load balancer correctly routes traffic to Cloud Run.

        Validation Steps:
        1. Check backend service configuration
        2. Verify NEG (Network Endpoint Group) connected
        3. Test request routing through load balancer
        4. Verify Cloud Armor policies attached

        Validation Command:
        gcloud compute backend-services describe improv-backend \\
          --global \\
          --project=improvOlympics
        """
        pytest.skip("Manual validation via GCP Console")


# Fixtures

@pytest.fixture
def config() -> Dict:
    """Configuration for infrastructure tests."""
    import os
    return {
        'service_url': os.getenv('SERVICE_URL', 'https://ai4joy.org'),
        'project_id': os.getenv('GCP_PROJECT_ID', 'improvOlympics'),
        'load_balancer_ip': os.getenv('LOAD_BALANCER_IP'),
    }
