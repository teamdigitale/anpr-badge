import flask
import pytest
from werkzeug.exceptions import HTTPException

import main


@pytest.fixture(scope="module")
def app():
    return flask.Flask(__name__)


codici_istat = ["059011", "016024", "059028"]


@pytest.mark.parametrize("codice_istat", codici_istat)
def test_badge(app, codice_istat):
    """Create three badges with existing cities."""
    with app.test_request_context(path="/" + codice_istat):
        res, *_ = main.badge(flask.request)
        data = res

        assert "xml" in data, data

#
# Test bad or missing data.
#
def test_comune_missing(app):
    with app.test_request_context(path="/" + "missing"):
        with pytest.raises(HTTPException) as exc:
            main.badge(flask.request)
        assert exc.value.response.status_code == 404
        assert b"missing" in exc.value.response.data


def test_comune_empty(app):
    with app.test_request_context(path="/"):
        with pytest.raises(HTTPException) as exc:
            main.badge(flask.request)
        assert exc.value.response.status_code == 400
        assert b"ISTAT" in exc.value.response.data


def test_badge_xss(app):
    with app.test_request_context(path="/<script>alert(1)</script>"):
        with pytest.raises(HTTPException) as exc:
            main.badge(flask.request)
        # Should be ascii error in description.
        assert exc.value.response.status_code == 400
        assert b"ascii" in exc.value.response.data


def test_parse_data():
    data = {
        "result": "ok",
        "error": "",
        "data": [
            {
                "CodiceIstat": "016024",
                "Name": "BERGAMO",
                "DataSubentro": "2018-05-17T00:00:00Z",
                "DataAbilitazione": "2017-11-08T00:00:00Z",
                "DataPresubentro": "2018-05-08T00:00:00Z",
                "PianificazioneIntervalloSubentro": {
                    "From": "2018-05-17T00:00:00Z",
                    "To": "2018-05-17T00:00:00Z",
                    "PreferredDate": "2018-05-17T00:00:00Z",
                    "IP": None,
                },
            }
        ],
    }
    comune, stato, color, logo = main.parse_response(data)
    assert color == "green"
