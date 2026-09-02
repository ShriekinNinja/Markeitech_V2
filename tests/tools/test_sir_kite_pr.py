"""Offline checks for the development-time GitHub App publishing boundary."""

import importlib.util
import json
from contextlib import contextmanager
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


def auth_responses(config, operation="pr"):
    token_permissions = {
        "pr": {"contents": "read", "metadata": "read", "pull_requests": "write"},
        "issue": {"metadata": "read", "issues": "write"},
    }
    return [
        {"id": config["app_id"], "slug": "sir-kite", "owner": {"login": "ShriekinNinja"}},
        {
            "app_id": config["app_id"],
            "account": {"login": "ShriekinNinja"},
            "repository_selection": "selected",
            "permissions": {
                "contents": "read",
                "metadata": "read",
                "pull_requests": "write",
                "issues": "write",
            },
        },
        {"token": "fixture-token", "permissions": token_permissions[operation]},
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


@pytest.mark.parametrize("operation", ["pr", "issue"])
@pytest.mark.parametrize(
    ("permission", "value"),
    [("contents", "write"), ("administration", "write"), ("issues", None), ("issues", "read")],
)
def test_unapproved_installation_stops_before_issuing_token(
    config, monkeypatch, operation, permission, value
):
    responses = auth_responses(config)
    if value is None:
        del responses[1]["permissions"][permission]
    else:
        responses[1]["permissions"][permission] = value
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises(ValueError, match="approved scope"):
        with kite.installation_token(config, operation=operation):
            pytest.fail("Must not admit unapproved installation permissions")
    assert api.call_count == 2


@pytest.mark.parametrize(
    ("operation", "permissions"),
    [
        ("pr", {"contents": "read", "metadata": "read", "pull_requests": "write"}),
        ("issue", {"metadata": "read", "issues": "write"}),
    ],
)
def test_approved_installation_grants_only_operation_permissions(
    config, monkeypatch, operation, permissions
):
    api = Mock(side_effect=auth_responses(config, operation))
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with kite.installation_token(config, operation=operation) as token:
        assert token == "fixture-token"
    assert api.call_args_list[2].args == (
        "/app/installations/456/access_tokens",
        "fixture-jwt",
        "POST",
        {"repository_ids": [789], "permissions": permissions},
    )
    assert api.call_args.args == ("/installation/token", "fixture-token", "DELETE")


@pytest.mark.parametrize("operation", ["pr", "issue"])
def test_overprivileged_token_is_rejected_and_revoked(config, monkeypatch, operation):
    responses = auth_responses(config, operation)
    responses[2]["permissions"] = dict(responses[1]["permissions"])
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises(ValueError, match="unexpected repository or permission scope"):
        with kite.installation_token(config, operation=operation):
            pytest.fail("Must not admit the full installation scope as an operation token")
    assert api.call_args.args == ("/installation/token", "fixture-token", "DELETE")


@pytest.mark.parametrize("operation", ["pr", "issue"])
@pytest.mark.parametrize("bad_scope", [False, True])
def test_issued_token_is_revoked_on_scope_or_operation_failure(
    config, monkeypatch, bad_scope, operation
):
    responses = auth_responses(config, operation)
    if bad_scope:
        responses[3]["total_count"] = 2
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises((ValueError, RuntimeError)):
        with kite.installation_token(config, operation=operation) as token:
            assert not bad_scope and token == "fixture-token"
            raise RuntimeError("Publication failed")
    assert api.call_args.args == ("/installation/token", "fixture-token", "DELETE")
    grant = api.call_args_list[2].args[3]
    assert grant["repository_ids"] == [config["repository_id"]]


def test_unknown_operation_is_rejected_before_authentication(config, monkeypatch):
    sign = Mock()
    monkeypatch.setattr(kite, "make_jwt", sign)
    with pytest.raises(ValueError, match="Unsupported publishing operation"):
        with kite.installation_token(config, operation="merge"):
            pytest.fail("Must not authenticate an unsupported operation")
    sign.assert_not_called()


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


def test_issue_creation_sends_body_and_labels_once(config, monkeypatch, tmp_path, capsys):
    body = tmp_path / "issue.md"
    body.write_text("Problem\n\nAcceptance criteria: preserve literal `$(example)`.")
    api = Mock(
        return_value={
            "number": 43,
            "html_url": "https://github.com/example/repo/issues/43",
            "user": {"login": "sir-kite[bot]"},
        }
    )
    monkeypatch.setattr(kite, "request", api)
    args = SimpleNamespace(title="Track a change", body_file=body, label=["enhancement"])
    kite.publish_issue(config, "fixture-token", args)
    api.assert_called_once_with(
        "/repos/ShriekinNinja/Markeitech_V2/issues",
        "fixture-token",
        "POST",
        {
            "title": "Track a change",
            "body": "Problem\n\nAcceptance criteria: preserve literal `$(example)`.",
            "labels": ["enhancement"],
        },
    )
    assert capsys.readouterr().out.splitlines() == [
        "https://github.com/example/repo/issues/43",
        "Author: sir-kite[bot]; issue: #43",
    ]


def test_issue_author_mismatch_reports_resource_without_retry(
    config, monkeypatch, tmp_path, capsys
):
    body = tmp_path / "issue.md"
    body.write_text("Fixture")
    api = Mock(
        return_value={
            "number": 43,
            "html_url": "https://github.com/example/repo/issues/43",
            "user": {"login": "ShriekinNinja"},
        }
    )
    monkeypatch.setattr(kite, "request", api)
    with pytest.raises(ValueError, match="unexpected issue author"):
        kite.publish_issue(
            config, "fixture-token", SimpleNamespace(title="Fixture", body_file=body, label=[])
        )
    assert api.call_count == 1
    assert capsys.readouterr().out == "https://github.com/example/repo/issues/43\n"
    assert "labels" not in api.call_args.args[3]


def test_issue_transport_failure_does_not_retry_or_expose_credentials(
    config, monkeypatch, tmp_path, capsys
):
    body = tmp_path / "issue.md"
    body.write_text("Fixture")
    responses = auth_responses(config, "issue")
    responses.insert(4, RuntimeError("sensitive response fixture"))
    api = Mock(side_effect=responses)
    monkeypatch.setattr(kite, "request", api)
    monkeypatch.setattr(kite, "make_jwt", lambda _: "fixture-jwt")
    monkeypatch.setattr(kite, "load_config", lambda _: config)
    monkeypatch.setattr(
        "sys.argv", [str(SCRIPT), "--issue", "--title", "Fixture", "--body-file", str(body)]
    )
    assert kite.main() == 1
    creations = [call for call in api.call_args_list if call.args[0].endswith("/issues")]
    assert len(creations) == 1
    assert api.call_args.args == ("/installation/token", "fixture-token", "DELETE")
    output = capsys.readouterr()
    assert "sensitive response" not in output.err
    assert "fixture-token" not in output.err
    assert "RuntimeError" in output.err
    assert output.out == ""


@pytest.mark.parametrize("operation", ["pr", "issue"])
@pytest.mark.parametrize("verify", [False, True])
def test_cli_selects_operation_and_verify_never_publishes(
    config, monkeypatch, tmp_path, operation, verify
):
    body = tmp_path / "body.md"
    body.write_text("Fixture")
    argv = [str(SCRIPT)]
    if verify:
        argv.append("--verify")
    else:
        argv += ["--title", "Fixture", "--body-file", str(body)]
        if operation == "pr":
            argv += ["--head", "fixture-branch"]
    if operation == "issue":
        argv.append("--issue")
    selected_operations = []

    @contextmanager
    def token_scope(actual_config, *, operation):
        assert actual_config == config
        selected_operations.append(operation)
        yield "fixture-token"

    pr = Mock()
    issue = Mock()
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setattr(kite, "load_config", lambda _: config)
    monkeypatch.setattr(kite, "installation_token", token_scope)
    monkeypatch.setattr(kite, "publish", pr)
    monkeypatch.setattr(kite, "publish_issue", issue)
    assert kite.main() == 0
    assert selected_operations == [operation]
    assert pr.call_count == int(not verify and operation == "pr")
    assert issue.call_count == int(not verify and operation == "issue")


@pytest.mark.parametrize(
    "arguments",
    [
        ["--issue", "--head", "fixture"],
        ["--issue", "--draft"],
        ["--issue"],
        ["--issue", "--title", "  ", "--body-file", "fixture.md"],
        ["--title", "Fixture", "--body-file", "fixture.md"],
    ],
)
def test_invalid_cli_arguments_fail_before_authentication(monkeypatch, arguments):
    load = Mock()
    monkeypatch.setattr(kite, "load_config", load)
    monkeypatch.setattr("sys.argv", [str(SCRIPT), *arguments])
    with pytest.raises(SystemExit) as exc:
        kite.main()
    assert exc.value.code == 2
    load.assert_not_called()


def test_group_readable_key_is_rejected(config, tmp_path):
    key = tmp_path / "fixture.pem"
    key.write_text("This is not a real key")
    key.chmod(0o640)
    config["private_key"] = str(key)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="only to its owner"):
        kite.load_config(path)
