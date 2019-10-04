# ANPR Badge API Wrapper

Questa PoC permette di generare un badge con lo stato di migrazione
ANPR dei comuni.


## test

Eseguire

  tox

## deploy

L'installazione su GCP avviene col comando

        gcloud functions deploy badge --runtime python37 --project anpr-badge --trigger-http

che restituisce l'URL di interrogazione

        curl -kv https://us-central1-anpr-badge.cloudfunctions.net/badge

### Tecnologia

L'API è basata sul quickstart di Google Cloud Functions

vedi:

* [Cloud Functions Hello World tutorial][tutorial]
* [Cloud Functions Hello World sample source code][code]

[tutorial]: https://cloud.google.com/functions/docs/quickstart
[code]: main.py

