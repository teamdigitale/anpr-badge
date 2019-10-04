import http.client as http_client
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import pytz
import requests
import yaml
from dateutil.parser import parse as dateparse
# This WILL be reported to Stackdriver Error Reporting
from flask import Response, abort, escape

import pybadges

http_client.HTTPConnection.debuglevel = 2
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


def _validate_parameters(request, mandatory_or, available=None):
    available = available or []
    available += mandatory_or

    if not any(x in mandatory_or for x in request.args):
        msg = f"At least one of the following parameter is required: {mandatory_or}"
        logging.error(RuntimeError(msg))
        problem(status=400, title=msg, args=request.path)

    for x in request.args:
        if x not in available:
            msg = f"Parameter not supported: {x}"
            logging.error(RuntimeError(msg))
            problem(status=400, title=msg, args=request.path)
        if not request.args[x].isalnum() or not request.args[x].isascii():
            msg = f"Only alphanumeric ascii characters are allowed for: {x}"
            logging.error(RuntimeError(msg))
            problem(status=400, title=msg, args=request.path)


def problem(
    status=500, title="Interal Server Error", type="about:blank", detail=None, **kwargs
):
    res = Response(
        status=status,
        response=json.dumps(
            dict(status=status, title=title, type=type, detail=detail, **kwargs)
        ),
        headers={"content-type": "application/problem+json"},
    )
    abort(res)


codici_istat = {"latina": "059011", "bergamo": "016024", "sezze": "059028"}


URL = "https://dashboard.anpr.it/api/comune/"


def get_day(datetime_rfc):
    return datetime_rfc.split("T", 1)[0]


def create_badge(dpath=None, **kwarg):
    svg = pybadges.badge(**kwarg)
    return svg


def parse_response(data):
    now = datetime.now(pytz.utc)

    try:
        comune = data["data"][0]
        denominazione = comune["Name"]
    except (KeyError, ValueError, IndexError, TypeError) as e:
        raise ValueError("Cannot parse entry: %r" % data)

    def milestone(event):
        if comune[event] and dateparse(comune[event]) <= now:
            return True
        return False

    if milestone("DataSubentro"):
        stato = "subentrato il " + get_day(comune["DataSubentro"])
        color = "green"
        logo = "https://stato-migrazione.anpr.it/img/hand_subentro.svg"
    elif milestone("DataPresubentro"):
        stato = "in presubentro dal" + get_day(comune["DataPresubentro"])
        color = "yellow"
        logo = "https://stato-migrazione.anpr.it/img/hand_presubentro.svg"
    else:
        stato = "inattivo :("
        color = "red"
        logo = "https://stato-migrazione.anpr.it/img/thumb-down.svg"

    return denominazione, stato, color, logo


def anpr_badge(codice_istat):
    try:
        url = f"https://dashboard.anpr.it/api/comune/{codice_istat}"
        res = requests.get(url)
    except Exception as e:
        problem(
            status=500,
            title="Internal Server Error",
            detail="Cannot contact remote url: %r" % url,
        )

    data = res.json()

    comune, stato, color, logo = parse_response(data)
    svg = create_badge(
        left_color="blue",
        right_color=color,
        left_text=f"Stato ANPR: {comune}",
        right_text=stato,
        logo=logo,
        embed_logo=True,
    )
    return svg


def _badge_get(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <http://flask.pocoo.org/docs/1.0/api/#flask.Request>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>.
    """
    request_args = request.args

    _validate_parameters(request, ["codice_istat"])
    codice_istat = request_args["codice_istat"]
    try:
        svg = anpr_badge(codice_istat)
    except ValueError as e:
        problem(
            status=404,
            title="Not Found",
            detail="Cannot find suitable data for %r" % codice_istat,
            instance=f"{URL}{codice_istat}",
        )
    except KeyboardInterrupt as e:
        problem(
            status=500,
            title="Internal Server Error",
            detail="Cannot create svg: %r" % e,
            args=request.path,
        )

    return (
        svg,
        200,
        {"Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=3600"},
    )


def badge(request):
    """Cloud Function endpoint
    """
    codice_istat = request.path.strip("/ ").split("/")
    if not codice_istat or not codice_istat[-1]:
        return problem(
            status=400,
            title="Bad Request",
            detail="Specifica il codice ISTAT del comune.",
            args=request.path,
        )

    codice_istat = codice_istat[-1]

    if codice_istat:
        request.args = {"codice_istat": codice_istat}
        return _badge_get(request)

    return {
        "/anpr-badge": "Hello World.",
        "/anpr-badge/{codice_istat}": "Ritorna un badge con lo stato di migrazione del tuo comune.",
    }
