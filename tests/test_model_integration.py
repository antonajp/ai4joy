"""
TC-003: Gemini Model Access
Tests connectivity to VertexAI Gemini models.
"""
import pytest
import time
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel


class TestModelIntegration:
    """Test suite for VertexAI Gemini model integration."""

    @pytest.fixture(scope="class", autouse=True)
    def init_vertexai(self, vertexai_config, gcp_credentials):
        """Initialize VertexAI with project settings."""
        aiplatform.init(
            project=vertexai_config['project_id'],
            location=vertexai_config['location']
        )

    @pytest.mark.integration
    def test_flash_model_access(self, vertexai_config):
        """Test access to gemini-1.5-flash model."""
        try:
            model = GenerativeModel(vertexai_config['flash_model'])

            test_prompt = "Say 'Hello from Flash' and nothing else."
            start_time = time.time()
            response = model.generate_content(test_prompt)
            latency = time.time() - start_time

            assert response.text is not None
            assert len(response.text) > 0
            assert latency < 3.0, f"Flash model latency {latency:.2f}s exceeds 3s threshold"

            print(f"Flash model response time: {latency:.2f}s")
            print(f"Response: {response.text}")

        except Exception as e:
            pytest.fail(f"Failed to access Flash model: {e}")

    @pytest.mark.integration
    def test_pro_model_access(self, vertexai_config):
        """Test access to gemini-1.5-pro model."""
        try:
            model = GenerativeModel(vertexai_config['pro_model'])

            test_prompt = "Say 'Hello from Pro' and nothing else."
            start_time = time.time()
            response = model.generate_content(test_prompt)
            latency = time.time() - start_time

            assert response.text is not None
            assert len(response.text) > 0
            assert latency < 5.0, f"Pro model latency {latency:.2f}s exceeds 5s threshold"

            print(f"Pro model response time: {latency:.2f}s")
            print(f"Response: {response.text}")

        except Exception as e:
            pytest.fail(f"Failed to access Pro model: {e}")

    @pytest.mark.integration
    def test_mc_agent_model_invocation(self, vertexai_config):
        """Test MC agent's model invocation."""
        try:
            model = GenerativeModel(vertexai_config['flash_model'])

            mc_prompt = """You are an energetic MC for an improv show.
            Welcome the audience and ask for a location suggestion.
            Keep your response under 50 words."""

            start_time = time.time()
            response = model.generate_content(mc_prompt)
            latency = time.time() - start_time

            assert response.text is not None
            assert "welcome" in response.text.lower() or "hello" in response.text.lower()
            assert latency < 3.0

            print(f"MC model latency: {latency:.2f}s")

        except Exception as e:
            pytest.fail(f"MC model invocation failed: {e}")

    @pytest.mark.integration
    def test_room_agent_sentiment_analysis(self, vertexai_config):
        """Test The Room agent's sentiment analysis capability."""
        try:
            model = GenerativeModel(vertexai_config['flash_model'])

            room_prompt = """You are simulating an improv audience's collective sentiment.
            Analyze this exchange and respond with: "Engaged", "Bored", or "Confused".
            Exchange: "Yes! And we should check the oxygen tanks!" / "Great idea! Let me grab the tools!"
            Respond with only one word."""

            start_time = time.time()
            response = model.generate_content(room_prompt)
            latency = time.time() - start_time

            assert response.text is not None
            sentiment = response.text.strip().lower()
            assert sentiment in ["engaged", "bored", "confused"]
            assert latency < 3.0

            print(f"Room sentiment analysis latency: {latency:.2f}s")
            print(f"Detected sentiment: {sentiment}")

        except Exception as e:
            pytest.fail(f"Room sentiment analysis failed: {e}")

    @pytest.mark.integration
    def test_partner_agent_creative_generation(self, vertexai_config):
        """Test Dynamic Scene Partner's creative response generation."""
        try:
            model = GenerativeModel(vertexai_config['pro_model'])

            partner_prompt = """You are an improv scene partner. Your partner just said:
            "We need to fix the broken airlock before we run out of oxygen!"

            Respond in character as a fellow astronaut. Use "Yes-And" technique.
            Keep response under 30 words. Be creative and heighten the stakes."""

            start_time = time.time()
            response = model.generate_content(
                partner_prompt,
                generation_config={"temperature": 0.9}
            )
            latency = time.time() - start_time

            assert response.text is not None
            assert len(response.text.split()) <= 50  # Rough word count check
            assert latency < 5.0

            print(f"Partner creative generation latency: {latency:.2f}s")
            print(f"Response: {response.text}")

        except Exception as e:
            pytest.fail(f"Partner creative generation failed: {e}")

    @pytest.mark.integration
    def test_coach_agent_analysis(self, vertexai_config):
        """Test Coach agent's analytical capability."""
        try:
            model = GenerativeModel(vertexai_config['pro_model'])

            coach_prompt = """You are an improv coach analyzing a student's performance.
            The student said: "Yes! And we should also check the backup systems!"

            Identify one improv principle they demonstrated. Keep response under 40 words."""

            start_time = time.time()
            response = model.generate_content(coach_prompt)
            latency = time.time() - start_time

            assert response.text is not None
            assert latency < 5.0

            print(f"Coach analysis latency: {latency:.2f}s")
            print(f"Analysis: {response.text}")

        except Exception as e:
            pytest.fail(f"Coach analysis failed: {e}")

    @pytest.mark.integration
    def test_concurrent_model_calls(self, vertexai_config):
        """Test concurrent calls to both models (simulating multi-agent orchestration)."""
        import concurrent.futures

        def call_flash():
            model = GenerativeModel(vertexai_config['flash_model'])
            start = time.time()
            response = model.generate_content("Say 'Flash'")
            return time.time() - start, response.text

        def call_pro():
            model = GenerativeModel(vertexai_config['pro_model'])
            start = time.time()
            response = model.generate_content("Say 'Pro'")
            return time.time() - start, response.text

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                flash_future = executor.submit(call_flash)
                pro_future = executor.submit(call_pro)

                flash_latency, flash_text = flash_future.result(timeout=10)
                pro_latency, pro_text = pro_future.result(timeout=10)

                assert flash_text is not None
                assert pro_text is not None
                print(f"Concurrent call latencies - Flash: {flash_latency:.2f}s, Pro: {pro_latency:.2f}s")

        except Exception as e:
            pytest.fail(f"Concurrent model calls failed: {e}")

    @pytest.mark.integration
    @pytest.mark.slow
    def test_model_quota_awareness(self, vertexai_config):
        """Test system behavior under API rate limiting."""
        # This test makes multiple rapid requests to observe quota handling
        model = GenerativeModel(vertexai_config['flash_model'])

        success_count = 0
        rate_limit_count = 0

        for i in range(10):
            try:
                response = model.generate_content(f"Count: {i}")
                if response.text:
                    success_count += 1
            except Exception as e:
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    rate_limit_count += 1
                    print(f"Hit rate limit on request {i}")
                else:
                    raise

        print(f"Successful requests: {success_count}, Rate limited: {rate_limit_count}")
        assert success_count > 0, "No requests succeeded"
