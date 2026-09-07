import json
import logging
import os
import shutil
import tempfile

import docker
from docker.errors import ContainerError, DockerException, ImageNotFound

logger = logging.getLogger(__name__)

SANDBOX_IMAGE = "securify-sandbox:latest"
CONTAINER_TIMEOUT_SECONDS = 60
CONTAINER_MEMORY_LIMIT = "512m"
CONTAINER_CPU_QUOTA = 100_000  # with cpu_period=100_000, this caps the container at 1 full CPU


class SandboxError(Exception):
    """Raised when the sandboxed parse/static-analysis run fails, times out,
    or the sandbox image isn't available."""


def run_parse_and_static_scan(input_dir: str) -> dict:
    """Runs Terraform parsing + Checkov for an uploaded .tf file inside an
    isolated, ephemeral `securify-sandbox` container, instead of in this
    backend/worker process.

    Before Phase 7 Part 5, hcl2.load() and the `checkov` subprocess both
    ran directly in the same process holding OPENAI_API_KEY and
    DATABASE_URL. An uploaded .tf file -- or a Checkov check it happens to
    trigger -- had no technical barrier stopping it from reading those, or
    reaching out over the network. This function is the barrier:
      - the container gets NO environment variables at all
      - the container has no network access whatsoever (network_disabled)
      - its root filesystem is read-only; only /output is writable
      - it's capped on memory and CPU, and killed if it runs past
        CONTAINER_TIMEOUT_SECONDS
      - it's force-removed whether it succeeds, fails, or times out

    input_dir must contain exactly the one uploaded .tf file for this scan
    (scan_service already lays storage out this way). Returns the sandbox's
    parsed result: {"parsed": ..., "raw_blocks": ..., "checkov_raw": ...} --
    the same three things scan_service used to get by calling
    parse_terraform_file / extract_raw_resource_blocks / run_checkov
    in-process.
    """
    try:
        client = docker.from_env()
    except DockerException as e:
        raise SandboxError(f"Could not reach Docker to launch the sandbox: {e}") from e

    output_dir = tempfile.mkdtemp(prefix="securify_sandbox_out_")
    os.chmod(output_dir, 0o777)  # sandbox runs as uid 1000, not this process's user

    container = None
    try:
        try:
            container = client.containers.run(
                SANDBOX_IMAGE,
                detach=True,
                remove=False,  # remove manually below, after reading /output
                network_disabled=True,
                read_only=True,
                tmpfs={"/tmp": "size=64m"},
                mem_limit=CONTAINER_MEMORY_LIMIT,
                cpu_period=100_000,
                cpu_quota=CONTAINER_CPU_QUOTA,
                security_opt=["no-new-privileges"],
                environment={},  # deliberately empty -- no OPENAI_API_KEY, no cloud creds, nothing
                volumes={
                    os.path.abspath(input_dir): {"bind": "/input", "mode": "ro"},
                    os.path.abspath(output_dir): {"bind": "/output", "mode": "rw"},
                },
            )
        except ImageNotFound as e:
            raise SandboxError(
                f"Sandbox image '{SANDBOX_IMAGE}' not found -- build it with "
                f"`docker-compose build sandbox` first"
            ) from e

        try:
            wait_result = container.wait(timeout=CONTAINER_TIMEOUT_SECONDS)
            exit_code = wait_result.get("StatusCode", -1)
        except Exception:
            logger.error("Sandbox container exceeded %ds timeout -- killing it", CONTAINER_TIMEOUT_SECONDS)
            try:
                container.kill()
            except DockerException:
                pass
            raise SandboxError(f"Sandboxed parse/static-analysis timed out after {CONTAINER_TIMEOUT_SECONDS}s")

        logs = container.logs().decode("utf-8", errors="replace")
        if exit_code not in (0, 1):
            # sandbox_runtime.py always exits 0 -- Checkov's own non-zero
            # exit (it found failing checks) never propagates out, since
            # sandbox_runtime.py only shells out to it and always finishes
            # normally afterward. Anything else here is a real sandbox failure.
            logger.error("Sandbox container exited %d. Logs: %s", exit_code, logs[-2000:])
            raise SandboxError(f"Sandboxed run failed (exit {exit_code})")

        result_path = os.path.join(output_dir, "result.json")
        if not os.path.exists(result_path):
            logger.error("Sandbox container produced no result.json. Logs: %s", logs[-2000:])
            raise SandboxError("Sandboxed run produced no output")

        with open(result_path) as f:
            result = json.load(f)

        if "error" in result and "parsed" not in result:
            raise SandboxError(f"Sandbox reported an error: {result['error']}")

        return result

    except (ContainerError, DockerException) as e:
        logger.exception("Docker error running sandbox")
        raise SandboxError(str(e)) from e
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass
        shutil.rmtree(output_dir, ignore_errors=True)
