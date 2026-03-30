import os
import argparse
import datetime
import json
import time
import urllib.error
import urllib.request

from huggingface_hub import HfApi, create_repo, get_token


def _resolve_token(cli_token: str | None) -> str | None:
    # Prefer explicit CLI arg, then env vars, then token saved by `hf auth login`.
    token = cli_token or os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if token:
        return token
    try:
        return get_token()
    except Exception:
        return None


def deploy(repo_id: str, folder_path: str, token: str | None, private: bool = False) -> None:
    api = HfApi(token=token) if token else HfApi()

    print(f"Ensuring repo exists: {repo_id}")
    create_kwargs = dict(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="docker",
        private=private,
        exist_ok=True,
    )
    if token:
        create_kwargs["token"] = token
    create_repo(**create_kwargs)
    print("Repo is ready.")

    print(f"Uploading folder content: {folder_path} -> {repo_id}")
    upload_kwargs = dict(folder_path=folder_path, repo_id=repo_id, repo_type="space")
    if token:
        upload_kwargs["token"] = token
    api.upload_folder(**upload_kwargs)
    print(f"Successfully uploaded to https://huggingface.co/spaces/{repo_id}")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _derive_space_url(repo_id: str) -> str:
    username, space_name = repo_id.split("/", 1)
    return f"https://{username}-{space_name}.hf.space"


def _space_stage(api: HfApi, repo_id: str) -> str:
    try:
        info = api.space_info(repo_id=repo_id)
        runtime = getattr(info, "runtime", None)
        if runtime is None:
            return "unknown"
        stage = getattr(runtime, "stage", None) or getattr(runtime, "status", None)
        return str(stage) if stage is not None else "unknown"
    except Exception:
        return "unknown"


def _http_get(url: str, timeout_seconds: float = 5.0, no_proxy: bool = True) -> tuple[int, str]:
    req = urllib.request.Request(
        url, method="GET", headers={"User-Agent": "meta-hackathon/push_to_hf"}
    )
    try:
        opener = (
            urllib.request.build_opener(urllib.request.ProxyHandler({}))
            if no_proxy
            else urllib.request.build_opener()
        )
        with opener.open(req, timeout=timeout_seconds) as resp:
            body = resp.read(2048).decode("utf-8", errors="replace")
            return int(resp.status), body
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2048).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return int(e.code), body
    except Exception as e:
        return 0, str(e)


def wait_for_space(
    repo_id: str,
    token: str | None,
    base_url: str | None,
    timeout_seconds: int,
    poll_seconds: int,
    no_proxy: bool,
    skip_stage: bool,
) -> int:
    api = HfApi(token=token) if token else HfApi()
    resolved_base = (base_url or _derive_space_url(repo_id)).rstrip("/")
    health_url = f"{resolved_base}/health"

    print(f"[{_now()}] Waiting for Space readiness: {health_url}")
    start = time.time()
    attempt = 0

    while True:
        attempt += 1
        elapsed = int(time.time() - start)
        if elapsed > timeout_seconds:
            print(f"[{_now()}] Timeout after {elapsed}s waiting for {health_url}")
            return 2

        stage = "skipped" if skip_stage else _space_stage(api, repo_id)
        code, body = _http_get(health_url, timeout_seconds=5.0, no_proxy=no_proxy)
        preview = body.replace("\r", "").replace("\n", " ")[:200]
        print(
            f"[{_now()}] attempt={attempt} elapsed={elapsed}s stage={stage} health_http={code} body='{preview}'"
        )

        if code == 200:
            try:
                json.loads(body)
            except Exception:
                pass
            return 0

        time.sleep(max(1, int(poll_seconds)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo_id", default="Samarth1401/context-router")
    parser.add_argument("--folder", default="hf_deployment")
    parser.add_argument("--token", default=None, help="HF Write Token (optional if already logged in via `hf auth login`)")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--wait", action="store_true", help="After upload, poll /health and Space runtime status until ready")
    parser.add_argument("--wait-only", action="store_true", help="Do not call Hugging Face API (no create/upload); only poll /health")
    parser.add_argument("--base-url", default=None, help="Override Space base URL (e.g. https://user-space.hf.space)")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Max seconds to wait for Space readiness (default 900)")
    parser.add_argument("--poll-seconds", type=int, default=5, help="Polling interval seconds (default 5)")
    parser.add_argument("--no-proxy", action="store_true", help="Bypass HTTP(S)_PROXY env vars when polling /health")
    args = parser.parse_args()

    if args.wait_only:
        return wait_for_space(
            repo_id=args.repo_id,
            token=None,
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
            no_proxy=bool(args.no_proxy),
            skip_stage=True,
        )

    token = _resolve_token(args.token)
    if not token:
        print("Error: no token found. Run `hf auth login` or set HF_TOKEN / HUGGING_FACE_HUB_TOKEN, or pass --token.")
        return 1

    deploy(args.repo_id, args.folder, token, args.private)
    if args.wait:
        return wait_for_space(
            repo_id=args.repo_id,
            token=token,
            base_url=args.base_url,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
            no_proxy=bool(args.no_proxy),
            skip_stage=False,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
