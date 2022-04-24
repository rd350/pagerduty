Use the Pagerduty API to acknowledge, resolve and add notes to incidents

_________________________________________________________________________
usage: manage_incidents_and_notes.py [-h] {ack,resolve-all,add-notes} ...

Acknowledge, resolve and add notes to pagerduty incidents

positional arguments:
  {ack,resolve-all,add-notes}
    ack                 Acknowledge all my triggered incidents
    resolve-all         Resolve my acknowledged incidents
    add-notes           Add notes to resolved incidents

optional arguments:
  -h, --help            show this help message and exit

Requirements: install pdpyras lib (pip install pdpyras) and export PD_API_KEY