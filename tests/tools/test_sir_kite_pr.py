"""Offline checks for the development-time GitHub App publishing boundary."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/sir-kite-pr.py"
SPEC = importlib.util.spec_from_file_location("sir_kite_pr", SCRIPT)
kite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kite)


@pytest.fixture
def config():
    return {
        "app_id": 123,
        "client_id": "fixture-client",
        "installation_id": 456,
        "repository_id": 789,
        "repository": "ShriekinNinja/Markeitech_V2",
        "owner": "ShriekinNinja",
        "slug": "sir-kite",
        "private_key": "/unused/key.pem",
    }


def auth_responses(config):
    return [
        {"id": config["app_id"], "slug": "sir-kite", "owner": {"login": "ShriekinNinja"}},
        {
            "app_id": config["app_id"],
            "account": {"login": "ShriekinNinja"},
            "repository_selection": "selected",
            "permissions": dict(kite.EXPECTED_PERMISSIONS),
        },
        {"token": "fixture-token", "permissions": dict(kite.EXPECTED_PERMISSIONS)},
        {
            "total_count": 1,
            "repositories": [
                {"id": config["repository_id"], "full_name": config["repository"]},
            ],
        },
        None,
    ]


def test_curl_keeps_credentials_out_of_arguments_and_ignores_user_config(monkeypatch, capsys):
    run = Mock(return_value=SimpleNamespace(returncode=0, stdout=b'{"ok":true}'))
    monkeypatch.setattr(kite.subprocess, "run", run)
    assert kite.request("/app", "fixture-secret") == {"ok": True}
    command = run.call_args.args[0]
    assert command[:2] == ["curl", "--disable"]
    assert "fixture-secret" not in " ".join(command)
    assert "--location" not in command and "--insecure" not in command
    assert b"Authorization: Bearer fixture-secret\n" in run.call_args.kwargs["input"]
    assert capsys.readouterr().out == ""


def test_permission_expansion_stops_before_issuing_token(config, monkeypatch):
    responses = auth_responses(config)
    responses[1]["permissions"]["contents"] = "write"
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises(ValueError, match="approved scope"):
        with kite.installation_token(config):
            pytest.fail("Must not admit expanded permissions")
    assert api.call_count == 2


@pytest.mark.parametrize("bad_scope", [False, True])
def test_issued_token_is_revoked_on_scope_or_operation_failure(config, monkeypatch, bad_scope):
    responses = auth_responses(config)
    if bad_scope:
        responses[3]["total_count"] = 2
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises((ValueError, RuntimeError)):
        with kite.installation_token(config) as token:
            assert not bad_scope and token == "fixture-token"
            raise RuntimeError("Publication failed")
    assert api.call_args.args == ("/installation/token", "fixture-token", "DELETE")
    grant = api.call_args_list[2].args[3]
    assert grant["repository_ids"] == [config["repository_id"]]


def test_owner_authored_pr_is_not_modified(config, monkeypatch):
    api = Mock(return_value=[{"user": {"login": "ShriekinNinja"}}])
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises(ValueError, match="different author"):
        kite.publish(config, "fixture-token", SimpleNamespace(head="fixture-branch"))
    assert api.call_count == 1


def test_new_bot_pr_requests_owner_review_and_labels(config, monkeypatch, tmp_path):
    body = tmp_path / "body.md"
    body.write_text("Fixture PR body")
    api = Mock(
        side_effect=[
            [],
            {
                "number": 42,
                "html_url": "https://github.com/example/repo/pull/42",
                "user": {"login": "sir-kite[bot]"},
                "draft": False,
                "head": {"sha": "fixture-sha"},
            },
            {"users": []},
            {},
            {},
        ]
    )
    monkeypatch.setattr(kite, "request", api)
    args = SimpleNamespace(
        head="fixture-branch",
        title="Fixture",
        body_file=body,
        draft=False,
        label=["enhancement"],
    )
    kite.publish(config, "fixture-token", args)
    assert api.call_args_list[1].args[3]["base"] == "master"
    assert api.call_args_list[3].args[3] == {"reviewers": ["ShriekinNinja"]}
    assert api.call_args_list[4].args[3] == {"labels": ["enhancement"]}


def test_group_readable_key_is_rejected(config, tmp_path):
    key = tmp_path / "fixture.pem"
    key.write_text("This is not a real key")
    key.chmod(0o640)
    config["private_key"] = str(key)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="only to its owner"):
        kite.load_config(path)
