import os
import subprocess
from pathlib import Path


def write_fake_docker(tmp_path: Path) -> tuple[Path, Path]:
    docker_log = tmp_path / "docker.log"
    docker = tmp_path / "docker"
    docker.write_text(
        """#!/bin/sh
set -eu
printf '%s\\n' "$*" >> "$DOCKER_LOG"
if [ "${1:-}" = "image" ] && [ "${2:-}" = "inspect" ]; then
    exit 1
fi
if [ "${1:-}" = "save" ]; then
    printf '%s' "$4" > "$3"
fi
""",
        encoding="utf-8",
    )
    docker.chmod(0o700)
    return docker, docker_log


def test_security_scan_can_export_the_checked_image(tmp_path: Path) -> None:
    _, docker_log = write_fake_docker(tmp_path)
    exported_image = tmp_path / "auth-api-image.tar"
    environment = {
        **os.environ,
        "DOCKER_LOG": str(docker_log),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
    }

    subprocess.run(  # noqa: S603 - repository script receives a controlled temp path
        [
            "/bin/bash",
            "scripts/docker_image_security.sh",
            "auth-api",
            "release-sha",
            "Dockerfile",
            ".",
            "trivy:test",
            str(exported_image),
        ],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        check=True,
    )

    assert exported_image.read_text(encoding="utf-8") == "auth-api:release-sha"


def test_publish_script_pushes_sha_and_latest_tags(tmp_path: Path) -> None:
    _, docker_log = write_fake_docker(tmp_path)
    environment = {
        **os.environ,
        "DOCKER_LOG": str(docker_log),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
    }

    subprocess.run(
        [
            "/bin/bash",
            "scripts/publish_image.sh",
            "auth-api:release-sha",
            "ghcr.io/alittlemore-dev/auth-api",
            "release-sha",
        ],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        check=True,
    )

    docker_calls = docker_log.read_text(encoding="utf-8").splitlines()
    assert docker_calls == [
        "tag auth-api:release-sha ghcr.io/alittlemore-dev/auth-api:release-sha",
        "tag auth-api:release-sha ghcr.io/alittlemore-dev/auth-api:latest",
        "push ghcr.io/alittlemore-dev/auth-api:release-sha",
        "push ghcr.io/alittlemore-dev/auth-api:latest",
    ]
