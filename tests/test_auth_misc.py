import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials

from app import auth
from app.misc import strtobool


def test_get_current_username_accepts_configured_user(monkeypatch):
    monkeypatch.setitem(auth.fake_users, "alice", "secret")

    username = auth.get_current_username(HTTPBasicCredentials(username="alice", password="secret"))

    assert username == "alice"


def test_get_current_username_rejects_invalid_user():
    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_username(HTTPBasicCredentials(username="missing", password="bad"))

    assert exc_info.value.status_code == 401


@pytest.mark.parametrize("value", [True, "yes", "true", "on", "1", "t", "y"])
def test_strtobool_true_values(value):
    assert strtobool(value) is True


@pytest.mark.parametrize("value", ["no", "false", "off", "0", "f", "n"])
def test_strtobool_false_values(value):
    assert strtobool(value) is False


def test_strtobool_rejects_unknown_value():
    with pytest.raises(ValueError, match="Invalid truth value"):
        strtobool("maybe")
