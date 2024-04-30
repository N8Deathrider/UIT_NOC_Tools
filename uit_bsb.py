#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import sys


def main():
    s = requests.session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                                    ' Chrome/98.0.4758.102 Safari/537.36'})
    apiKey = get_apikey(s)
    routes = get_routes(s, apiKey)
    bsb_route = sort_routes(routes, 'BSB-U Hospital')
    bsb_route_id = bsb_route['RouteID']
    bsb_route_stops = bsb_route['Stops']
    for stop in bsb_route_stops:
        if stop['RouteStopID'] == 693:
            bsb_hospital_stop = stop
        elif stop['RouteStopID'] == 698:
            bsb_102tower_stop = stop
    bsb_102tower_stop_time = time_until_arrival(s, bsb_102tower_stop['AddressID'], apiKey)
    bsb_hospital_stop_time = time_until_arrival(s, bsb_hospital_stop['AddressID'], apiKey)
    print(f"\n{bsb_102tower_stop['SignVerbiage']:>19}: {bsb_102tower_stop_time[0]['Times'][0]['Text']}\n"
          f"{bsb_hospital_stop['SignVerbiage']:>19}: {bsb_hospital_stop_time[0]['Times'][0]['Text']}\n")


def get_apikey(session) -> str:
    """
    Gets the API key and returns it for further use
    :param session: the current requests.session() object
    :return: key: the API key found from the request
    """
    url = 'https://uofu.ridesystems.net/Services/JSONPRelay.svc/GetMapConfig'
    r = session.get(url)
    if r.ok:
        key = r.json()['ApiKey']
        return key
    else:
        sys.exit(f'When trying to get the API key the script got a {r.status_code}')


def get_routes(session, key) -> list:
    """
    Attempts to return a list of routes
    :param session: the current requests.session() object
    :param key: valid API key
    :return: list of routes
    """
    url = 'https://uofu.ridesystems.net/Services/JSONPRelay.svc/GetRoutesForMapWithScheduleWithEncodedLine'
    parameters = {
        'apiKey': key,
        'isDispatch': False
    }
    r = session.get(url, params=parameters)
    if r.ok:
        return r.json()
    else:
        sys.exit('Something has gone wrong while trying to get the list of routes')


def sort_routes(routes_list, route_description) -> dict:
    """
    Returns the isolated dictionary for the desired route
    :param routes_list: list of route dictionaries
    :param route_description: description of the route you would like to isolate
    :return: the desired route
    """
    for route in routes_list:
        if route['Description'] == route_description:
            desired_route = route
    return desired_route


def time_until_arrival(session, stop_id, key):
    """
    Searches for the time until the next bus at a specific stop
    :param session: The current requests.session() object
    :param stop_id: The id of the stop to query
    :param key: Valid API key
    :return:
    """
    url = 'https://uofu.ridesystems.net/Services/JSONPRelay.svc/GetStopArrivalTimes'
    paramiters = {
        'apiKey': key,
        'stopIds': stop_id,
        'version': '2'
    }
    r = session.get(url, params=paramiters)
    # print(r.url)  # DEBUG
    if r.ok:
        return r.json()


if __name__ == '__main__':
    main()
