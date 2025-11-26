"""
TC-001: Container Build Verification
Tests that the Docker container builds successfully with all dependencies.
"""

import pytest
import docker
from pathlib import Path


class TestContainerBuild:
    """Test suite for container build verification."""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Docker client for container operations."""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def project_root(self):
        """Project root directory."""
        return Path(__file__).parent.parent

    def test_dockerfile_exists(self, project_root):
        """Verify Dockerfile exists in project root."""
        dockerfile = project_root / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile not found in project root"

    def test_requirements_exists(self, project_root):
        """Verify requirements.txt exists."""
        requirements = project_root / "requirements.txt"
        assert requirements.exists(), "requirements.txt not found"

    def test_container_build(self, docker_client, project_root):
        """
        Build Docker container and verify successful creation.
        This is the core test for TC-001.
        """
        image_tag = "improv-olympics:test"

        # Build the image
        try:
            image, build_logs = docker_client.images.build(
                path=str(project_root), tag=image_tag, rm=True, pull=True
            )

            # Print build logs for debugging
            for log in build_logs:
                if "stream" in log:
                    print(log["stream"].strip())

            assert image is not None, "Image build failed"
            assert image_tag in [tag for img_tags in image.tags for tag in img_tags]

        except docker.errors.BuildError as e:
            pytest.fail(f"Container build failed: {e}")

    def test_image_size(self, docker_client):
        """Verify container image size is reasonable (<2GB)."""
        image_tag = "improv-olympics:test"

        try:
            image = docker_client.images.get(image_tag)
            size_gb = image.attrs["Size"] / (1024**3)

            assert size_gb < 2.0, f"Image size {size_gb:.2f}GB exceeds 2GB limit"
            print(f"Image size: {size_gb:.2f}GB")

        except docker.errors.ImageNotFound:
            pytest.skip("Image not built, run test_container_build first")

    def test_image_layers(self, docker_client):
        """Inspect image layers for expected dependencies."""
        image_tag = "improv-olympics:test"

        try:
            image = docker_client.images.get(image_tag)
            history = image.history()

            # Check that we have a reasonable number of layers (not too many = inefficient)
            assert len(history) < 50, f"Too many layers: {len(history)}"
            print(f"Image has {len(history)} layers")

        except docker.errors.ImageNotFound:
            pytest.skip("Image not built, run test_container_build first")

    def test_required_packages_installed(self, docker_client):
        """Verify required packages are installed in container."""
        image_tag = "improv-olympics:test"

        required_packages = [
            "google-cloud-aiplatform",
            "google-generativeai",
            "pytest",
            "flask",  # or fastapi, depending on implementation
        ]

        try:
            # Run pip list inside container
            container = docker_client.containers.run(
                image_tag, command="pip list", remove=True, detach=False
            )

            installed_packages = container.decode("utf-8").lower()

            for package in required_packages:
                assert (
                    package.lower() in installed_packages
                ), f"Required package '{package}' not found in container"

        except docker.errors.ImageNotFound:
            pytest.skip("Image not built, run test_container_build first")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Failed to inspect container packages: {e}")

    def test_container_starts(self, docker_client):
        """Verify container starts without immediate errors."""
        image_tag = "improv-olympics:test"

        try:
            container = docker_client.containers.run(
                image_tag,
                detach=True,
                environment={"GOOGLE_APPLICATION_CREDENTIALS": "/tmp/dummy_creds.json"},
                remove=False,  # Keep for inspection
            )

            # Wait a few seconds to see if it crashes immediately
            import time

            time.sleep(3)

            container.reload()
            assert container.status in [
                "running",
                "created",
            ], f"Container failed to start, status: {container.status}"

            # Clean up
            container.stop(timeout=1)
            container.remove()

        except docker.errors.ImageNotFound:
            pytest.skip("Image not built, run test_container_build first")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Container failed to start: {e}")

    @pytest.mark.slow
    def test_container_cleanup(self, docker_client):
        """Clean up test container images."""
        image_tag = "improv-olympics:test"

        try:
            docker_client.images.remove(image_tag, force=True)
            print(f"Cleaned up test image: {image_tag}")
        except docker.errors.ImageNotFound:
            pass  # Already cleaned up
