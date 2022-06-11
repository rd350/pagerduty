#!/usr/bin/python3
"""
Acknowledge, resolve and add notes to pagerduty incidents
"""

import argparse
import json
import os
import requests
import sys
import pdpyras
from pdpyras import APISession
from requests.exceptions import HTTPError
from datetime import date, timedelta

URL = "https://api.pagerduty.com"
since = (date.today() - timedelta(1)).strftime('%Y-%m-%dT08:00:00+12:00')
until = (date.today() + timedelta(1)).strftime('%Y-%m-%dT08:00:00+12:00')

class PD():

    def __init__(self, api_key):
        """ Initiate session """

        # Using pdpyras for session
        self._api_key = api_key
        self.s        = APISession(self._api_key)

    def _me(self):
        """ Get user id, email, time zone and team id """

        # Using pdpyras for auth
        try:
            data = self.s.rget('users/me')
            for team in data['teams']:
                pass
            return (data['id'], data['email'], data['time_zone'], team['id'])

        except pdpyras.PDHTTPError as e:
            if e.response.status_code == 404:
                sys.exit("Your PD account does not exist?")
            else:
                sys.exit(e)

        except pdpyras.PDClientError as e:
            sys.exit("Non-transient network or client error")

    def _get_headers(self):
        """ Headers for GET requests """

        headers = {
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Authorization": f"Token token={self._api_key}",
            "Content-Type": "application/json"
        }
        return headers

    def _post_headers(self):
        """ Headers for POST requests """

        headers = self._get_headers()
        headers["From"] = f"{self._me()[1]}"
        return headers

    def _get_my_incidents(self, status=None):
        """
        Get all incidents escalated to user based on since, until and
        status of either triggered or acknowledged

        Pagination enabled
        """

        more = True
        limit = 100
        offset = 0
        incidents = []

        while more == True:
            url = f"{URL}/incidents"
            params = {
                "statuses[]": status,
                "user_ids[]": self._me()[0],
                "team_ids[]": self._me()[3],
                "time_zone" : self._me()[2],
                "since"     : since,
                "until"     : until,
                "sort_by"   : "incident_number:desc",
                "limit"     : limit,
                "offset"    : offset,
            }
            r = self.s.get(url, headers=self._get_headers(), params=params)
            data = r.json()

            for element in data['incidents']:
                incidents.append(element)

            offset = limit + offset

            # Loop until more is False for pagination
            more = data['more']

        if not data['incidents']:
            print ("No incidents found")

        return incidents

    def ack_all(self):
        """
        Acknowledge all the triggered incidents allocated to user
        """

        for incident in self._get_my_incidents('triggered'):
            print (f"Acknowledged {incident['title']} " \
                    f"(Incident id:{incident['incident_number']})")

            url = f"{URL}/incidents/{incident['id']}"
            data = {
                "incident": {
                    "type": "incident_reference",
                    "status": "acknowledged"
                }
            }
            self.s.put(
                url,
                headers=self._post_headers(),
                data=json.dumps(data)
            )

    def resolve_all(self):
        """
        Resolve all the acknowledged incidents allocated to user
        """

        for incident in self._get_my_incidents('acknowledged'):
            print (f"Resolved {incident['title']} " \
                    f"(Incident id:{incident['incident_number']})")
            url = f"{URL}/incidents/{incident['id']}"
            data = {
                "incident": {
                    "type": "incident_reference",
                    "status": "resolved"
                }
            }
            self.s.put(
                url,
                headers=self._post_headers(),
                data=json.dumps(data)
            )

    def _prompt(self):
        """
        User prompt for adding notes
        """

        note = input("Enter a note: ")
        return note

    def _resolve_prompt(self):
        """
        User prompt for resolving acknowledged incidents
        """

        i = input("\nWant me to resolve any pending ack'd incidents? (y/n): ")

        if (i.lower() == 'y'):
            return True
        elif (i.lower() == 'n'):
            return False
        else:
            sys.exit("WHAT?")

    def _list_notes(self, incident_id):
        """
        List note of an incident
        """

        url = f"{URL}/incidents/{incident_id}/notes"
        r = self.s.get(url, headers=self._get_headers())
        data = r.json()

        if not data['notes']:
            return False
        else:
            return True

    def _list_incidents(self):
        """
        List incidents to capture resolved incidents.

        Pagination is enabled.
        """

        more = True
        limit = 100
        offset = 0
        incidents = []

        while more == True:
            url = f"{URL}/incidents"
            params = {
                "statuses[]": "resolved",
                "include[]" : ['first_trigger_log_entries', 'channel'],
                "team_ids[]": self._me()[3],
                "time_zone" : self._me()[2],
                "since"     : since,
                "until"     : until,
                "sort_by"   : "incident_number:desc",
                "limit"     : limit,
                "offset"    : offset,
                "total"     : "true",
            }
            r = self.s.get(url, headers=self._get_headers(), params=params)
            data = r.json()

            for element in data['incidents']:
                incidents.append(element)

            offset = limit + offset
            more = data['more']

        if not data['incidents']:
            print ("No incidents found")

        return incidents

    def _list_log_entries(self):
        """
        List log entries.

        Pagination is enabled.
        """

        more = True
        limit = 100
        offset = 0
        log_entries = []

        while more == True:
            url = f"{URL}/log_entries"
            params = {
                "include[]"  : "incidents",
                "team_ids[]" : self._me()[3],
                "time_zone"  : self._me()[2],
                "since"      : since,
                "until"      : until,
                "limit"      : limit,
                "offset"     : offset,
                "is_overview": "true",
                "total"      : "true",
            }
            r = self.s.get(url, headers=self._get_headers(), params=params)
            data = r.json()

            for element in data['log_entries']:
                log_entries.append(element)

            offset = limit + offset
            more = data['more']

        return log_entries

    def _get_user_from_log(self, incident_id):
        """
        Get user id of a resolved incident by looking at the
        assign log entry
        """

        for log_entry in self._list_log_entries():
            if (log_entry['type'] == "assign_log_entry" and
                log_entry['agent']['id'] == self._me()[0] and
                log_entry['incident']['id'] == incident_id):
                match = True
                break
            match = False

        if match == True:
            return True
        else:
            return False

    def add_notes(self):
        """
        Add a note to resolved incidents
        """

        print("\nLooking for incidents that need notes added: ")

        for incident in self._list_incidents():

            # Get the user who acknowledged the incident because resolved
            # incidents do not have a user tied to it.
            if (self._get_user_from_log(incident['id']) == True):

                # Add a note if not added already
                if (self._list_notes(incident['id']) == False):
                    print(f"Adding note to {incident['summary']}")

                    url = f"{URL}/incidents/{incident['id']}/notes"
                    data = {
                        "note":{
                            "content": self._prompt()
                        },
                    }
                    self.s.post(
                        url,
                        headers=self._post_headers(),
                        data=json.dumps(data)
                    )
                    print("Done\n---------------------------------------------")

        print("All your incidents may have notes!")


def main():
    epilog = ("Requirements: install pdpyras lib (pip install pdpyras) and "
              "export PD_API_KEY")

    parser = argparse.ArgumentParser(description=__doc__, epilog=epilog)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True
    subparsers.add_parser('ack', help='Acknowledge all my triggered incidents')
    subparsers.add_parser('resolve-all', help='Resolve my acknowledged incidents')
    subparsers.add_parser('add-notes', help='Add notes to resolved incidents')
    args = parser.parse_args()

    try:
      api_key = os.environ['PD_API_KEY']
    except KeyError:
      sys.exit("Export your PD_API_KEY")

    pd = PD(api_key)

    try:
      if args.command == 'ack':
          pd.ack_all()
      elif args.command == 'resolve-all':
          pd.resolve_all()
      elif args.command == 'add-notes':
          pd.add_notes()
      else:
          raise NotImplementedError(f"no check matching {args.command}")

    except HTTPError as http_err:
      sys.stdout.write(f"{http_err} \n")
      sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(f"User interrupt caught...\nSee {__file__} --help")
