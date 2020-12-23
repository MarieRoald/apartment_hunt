import json
import random
import re
import sqlite3
from textwrap import dedent
from time import sleep

import pandas as pd
import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString
from selenium import webdriver
from tqdm import tqdm


def parse_price(price_string, currency="kr", divider="\xa0"):
    currency_stripped = price_string.strip(currency)
    return int(currency_stripped.replace(divider, ""))


def parse_area(area_string, unit):
    return float(area_string.split(unit)[0])


def parse_info(info_string):
    if info_string is None:
        return info_string
    if info_string.isdigit():
        return int(info_string)
    elif "kr" in info_string:
        return parse_price(info_string, currency="kr")
    elif "m²" in info_string:
        return parse_area(info_string, unit="m²")
    else:
        return info_string


def get_entur_location(adress):
    adress = re.sub(r"(\d)\s([a-zA-Z])", r"\1\2", adress)
    adress = re.sub(r"([(].*[)])", "", adress)
    adress = re.sub(r"([0-9][0-9][0-9][0-9]).*", "r\1 Oslo", adress)
    adress = adress.replace("r\x01", "").replace("8og ", "")
    endpoint = f"https://api.entur.io/geocoder/v1/autocomplete?text={adress}&lang=en"
    data = requests.get(endpoint).content

    return json.loads(data)["features"][0]


def request_walking_distance(start_coord, stop_coord, suffix):
    """Returns a dictionary with time to walk and walking distance between the coordinates."""
    start_lat, start_lon = start_coord
    stop_lat, stop_lon = stop_coord
    payload = (
        "{trip(from:{coordinates:{latitude:%s longitude:%s}}to:{coordinates:{latitude:%s longitude:%s}}modes:[foot]){tripPatterns{duration walkDistance}}}"
        % (start_lat, start_lon, stop_lat, stop_lon)
    )

    data = json.loads(
        requests.post(
            "https://api.entur.io/journey-planner/v2/graphql",
            headers={"Content-Type": "application/json", "ET-Client-Name": "privat - boligscraper"},
            data=f'{{"query": "{payload}"}}',
        ).content
    )
    try:
        data = {
            f"gåtid-{suffix}": int(data["data"]["trip"]["tripPatterns"][0]["duration"]) / 60,
            f"gåavstand-{suffix}": int(data["data"]["trip"]["tripPatterns"][0]["walkDistance"]),
        }
    except:
        data = {
            f"gåtid-{suffix}": None,
            f"gåavstand-{suffix}": None,
        }
    return data


def request_bike_distance(start_coord, stop_coord, suffix):
    """Return a singleton dictionary with the time to bike between the coordinates."""
    start_lat, start_lon = start_coord
    stop_lat, stop_lon = stop_coord
    payload = (
        "{trip(from:{coordinates:{latitude:%s longitude:%s}}to:{coordinates:{latitude:%s longitude:%s}}modes:[bicycle]){tripPatterns{duration walkDistance}}}"
        % (start_lat, start_lon, stop_lat, stop_lon)
    )

    data = json.loads(
        requests.post(
            "https://api.entur.io/journey-planner/v2/graphql",
            headers={"Content-Type": "application/json", "ET-Client-Name": "privat - boligscraper"},
            data=f'{{"query": "{payload}"}}',
        ).content
    )
    try:
        data = {
            f"sykkeltid-{suffix}": int(data["data"]["trip"]["tripPatterns"][0]["duration"] / 60)
        }
    except:
        data = {f"sykkeltid-{suffix}": None}
    return data


def request_public_transport_distance(start_coord, stop_coord, suffix):
    """Returns a singleton dictionary that contains the time to travel
    between the coordinates using public transport.
    """
    start_lat, start_lon = start_coord
    stop_lat, stop_lon = stop_coord
    payload = (
        "{trip(from:{coordinates:{latitude:%s longitude:%s}}to:{coordinates:{latitude:%s longitude:%s}}){tripPatterns{duration walkDistance}}}"
        % (start_lat, start_lon, stop_lat, stop_lon)
    )

    data = json.loads(
        requests.post(
            "https://api.entur.io/journey-planner/v2/graphql",
            headers={"Content-Type": "application/json", "ET-Client-Name": "privat - boligscraper"},
            data=f'{{"query": "{payload}"}}',
        ).content
    )
    try:
        data = {
            f"kollektivtid-{suffix}": min(
                int(trip_pattern["duration"] / 60)
                for trip_pattern in data["data"]["trip"]["tripPatterns"]
            )
        }
    except:
        data = {f"kollektivtid-{suffix}": None}
    return data


def get_commute_info(home_info):
    """Get the commute info for a specific listing.

    Returns a dictionary with walking distance and time to walk,
    bike and take public transport to UiO and OsloMet.
    """

    coordinates = (home_info["koordinat_lat"], home_info["koordinat_lon"])
    uio_coordinates = (59.9396, 10.7233)
    met_coordinates = (59.9225, 10.7327)

    uio_info = coordinates, uio_coordinates, "uio"
    met_info = coordinates, met_coordinates, "met"

    uio_walking_distance = request_walking_distance(*uio_info)
    met_walking_distance = request_walking_distance(*met_info)

    uio_bike_distance = request_bike_distance(*uio_info)
    met_bike_distance = request_bike_distance(*met_info)

    uio_public_transport_distance = request_public_transport_distance(*uio_info)
    met_public_transport_distance = request_public_transport_distance(*met_info)

    return {
        **uio_walking_distance,
        **uio_bike_distance,
        **uio_public_transport_distance,
        **met_walking_distance,
        **met_bike_distance,
        **met_public_transport_distance,
    }


def scrape_listing_info(URL):
    """Scrape all information about a single home listing."""
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")

    home_info = {
        "url": URL,
    }
    home_info["tittel"] = soup.find("h1", class_="u-t2").string

    # Get the adress
    home_info["adresse"] = soup.find("h1", class_="u-t2").find_next_sibling("p").string
    home_info["postnummer"] = re.search(r"\d{4}(?![0-9])", home_info["adresse"]).group(0)
    loc_tag = soup.find("h1", class_="u-t2").find_previous_sibling("span")
    if loc_tag is not None:
        home_info["location"] = loc_tag.string
    else:
        home_info["location"] = None

    # Price information, located just underneath the title
    price_string = soup.find("span", string="Prisantydning").find_next_sibling("span").string
    home_info["prisantydning"] = parse_price(price_string)
    for info_field in ["Omkostninger", "Totalpris", "Felleskost/mnd.", "Fellesgjeld"]:
        key = info_field.lower()

        try:
            info_string = soup.find("dt", string=info_field).find_next_sibling("dd").string
            value = parse_price(info_string)
        except AttributeError:
            value = None
        home_info[key] = value

    # Table with info before the text description
    home_info["boligtype"] = soup.find("dt", string="Boligtype").find_next_sibling("dd").string
    for info_field in soup.find("dt", string="Boligtype").find_next_siblings("dt"):
        info_field = info_field.string

        key = info_field.lower()
        info_string = "".join(
            (soup.find("dt", string=info_field).find_next_sibling("dd").stripped_strings)
        )
        home_info[key] = parse_info(info_string)

    # Hidden table with info that we can reveal by pressing "+ Flere detaljer"
    definition_lists = soup.find(attrs={"data-controller": "moreKeyInfo"}).find_all(
        "dl", class_="definition-list"
    )
    for definition_list in definition_lists:
        for element in definition_list.find_all("dt"):
            info_field = element.string
            key = info_field.lower()
            info_string = "".join(
                (soup.find("dt", string=info_field).find_next_sibling("dd").stripped_strings)
            )
            home_info[key] = parse_info(info_string)

    # Get entur location and commute info
    entur_loc = get_entur_location(home_info["adresse"])
    home_info[
        "adresse_for_reisevei"
    ] = f"{entur_loc['properties']['name']}, {entur_loc['properties']['postalcode']}"

    home_info["koordinat_lon"] = entur_loc["geometry"]["coordinates"][0]
    home_info["koordinat_lat"] = entur_loc["geometry"]["coordinates"][1]

    home_info = {
        **home_info,
        **get_commute_info(home_info),
    }

    return home_info


def find_listings(URL, *, urls=None, browser=None):
    if browser is None:
        browser = webdriver.Chrome("./chromedriver")
    if urls is None:
        urls = []
    browser.get(URL)
    soup = BeautifulSoup(browser.page_source, "html.parser")

    for boliglink in soup.find_all("a", class_="ads__unit__link"):
        if "https" not in boliglink["href"]:
            continue
        urls.append(f"{boliglink['href']}")

    next_link_class = "button button--pill button--has-icon button--icon-right"
    try:
        next_link = next(iter(soup.find_all("a", class_=next_link_class)))["href"]
        next_link = f"https://finn.no/realestate/homes/search.html{next_link}"
    except StopIteration:
        next_link = None

    if next_link is not None:
        sleep(random.uniform(0, 5))
        return find_listings(next_link, urls=urls, browser=browser)

    return next_link, urls, browser


if __name__ == "__main__":
    # Get relevant apartment listings
    search_url = "https://www.finn.no/realestate/homes/search.html?lifecycle=1&location=1.20061.20507&location=1.20061.20515&location=1.20061.20512&location=1.20061.20511&location=1.20061.20522&location=1.20061.20510&location=1.20061.20513&location=1.20061.20509&location=1.20061.20508&location=1.20061.20531&property_type=3"
    _, URLs, browser = find_listings(search_url)
    browser.close()

    # Scrape all apartment listings
    data = []
    previous_urls = set()  # Used to skip duplicates
    for url in tqdm(URLs):
        # Prosjekt listings have no price, so we skip them
        # We also skip listings that have been scraped before
        if "prosjekt" in url or url in previous_urls:
            continue
        data.append(scrape_listing_info(url))
        sleep(random.uniform(0, 2))
        previous_urls.add(url)

    # Get all columns and their types for the SQL database
    types = {NavigableString: 'text', str: 'text', int: 'integer', float: 'real'}
    column_types = {}
    for row in data:
        for key, value in row.items():
            if value is None:
                continue
            column_types[key] = types[type(value)]
    
    del column_types['url']

    # Generate query to create the SQL table
    create_table_query = dedent("""\
    CREATE TABLE IF NOT EXISTS boligdata (
        url text PRIMARY KEY
    """)
    for name, datatype in column_types.items():
        create_table_query += f',\n    "{name}" {datatype}'
    create_table_query += ")"

    # Generate and populate the SQL table, overwriting existing tables
    with sqlite3.connect("boligdata.db") as connection:
        c = connection.cursor()
        c.execute("DROP TABLE IF EXISTS boligdata")
        c.execute(create_table_query)
        for row in data:
            columns = ", ".join(f'"{s}"' for s in row.keys())
            values = list(row.values())
            value_placeholders = ", ".join("?"*len(values))
            c.execute(f'INSERT INTO boligdata ({columns}) VALUES ({value_placeholders});', values)
