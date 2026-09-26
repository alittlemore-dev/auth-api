import os
import subprocess
from pathlib import Path


def test_run_loads_public_key_from_file(tmp_path: Path) -> None:
    public_key_file = tmp_path / "public-key"
    public_key_file.write_text("PUBLIC\\nKEY", encoding="utf-8")
    captured_key_file = tmp_path / "captured-key"
    granian = tmp_path / "granian"
    granian.write_text(
        '#!/bin/sh\nprintf "%s" "$AUTH_PUBLIC_KEY" > "$CAPTURED_KEY_FILE"\n',
        encoding="utf-8",
    )
    granian.chmod(0o700)
    environment = {
        **os.environ,
        "AUTH_PUBLIC_KEY_FILE": str(public_key_file),
        "CAPTURED_KEY_FILE": str(captured_key_file),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
    }
    environment.pop("AUTH_PUBLIC_KEY", None)

    subprocess.run(
        ["/bin/bash", "start_application.sh", "run"],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        check=True,
    )

    assert captured_key_file.read_text(encoding="utf-8") == "PUBLIC\nKEY"


def test_run_loads_telegram_service_secret_from_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "telegram-service-secret"
    secret_file.write_text("TEST_SERVICE_SECRET\n", encoding="utf-8")
    captured_file = tmp_path / "captured-secret"
    granian = tmp_path / "granian"
    granian.write_text(
        '#!/bin/sh\nprintf "%s\\n%s" "$TELEGRAM_SERVICE_SECRET" '
        '"${TELEGRAM_SERVICE_SECRET_FILE-unset}" > "$CAPTURED_FILE"\n',
        encoding="utf-8",
    )
    granian.chmod(0o700)
    environment = {
        **os.environ,
        "TELEGRAM_SERVICE_SECRET_FILE": str(secret_file),
        "CAPTURED_FILE": str(captured_file),
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
    }
    environment.pop("TELEGRAM_SERVICE_SECRET", None)

    subprocess.run(
        ["/bin/bash", "start_application.sh", "run"],
        cwd=Path(__file__).resolve().parents[3],
        env=environment,
        check=True,
    )

    assert captured_file.read_text(encoding="utf-8") == "TEST_SERVICE_SECRET\nunset"
