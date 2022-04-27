#!/usr/bin/python3
"""
Monitoring Pagerduty status for outages
"""

import json
import requests
import argparse
import sys

NAGIOS_OK = 0
NAGIOS_WARNING = 1
NAGIOS_UNKNOWN = 3

r = requests.get("https://status.pagerduty.com/api/v2/status.json")
data = r.json()

def status():
    if r.ok:
        if data['status']['description'] == "All Systems Operational":
            return (NAGIOS_OK, f"Status OK: {data['status']['description']}")
        else:
            return (NAGIOS_WARNING, f"Indicator: {data['status']['indicator']}", \
                                      f"\nStatus: {data['status']['description']}")
    else:
        return(NAGIOS_UNKNOWN, "status.pagerduty.com is down")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=['show'])
    args = parser.parse_args()

    if args.check == 'show':
        return_code, description = status()

    sys.stdout.write(description + '\n')
    sys.exit(return_code)


if __name__ == '__main__':
    main()
