# Class to contain data for each address and associated location data

import random
import time
import urllib
from copy import copy
from dataclasses import asdict, dataclass, field
from string import digits as DIGITS

import requests
from geopy.geocoders import GoogleV3

_PO_BOX_CHECKS = {
    "POBOX",
    "PO BOX",
    "P O BOX",
    "P.O BOX",
    "P.OBOX",
    "P. O BOX",
    "PO. BOX",
    "PO.BOX",
    "P O. BOX",
    "P.O. BOX",
    "P. O. BOX",
    "P.O.BOX",
}

_MILITARY_MAIL_POST_OFFICE = {"APO", "FPO", "DPO"}
_MILITARY_MAIL_STATES = {"AA", "AP", "AE"}

FCC_API_URL = "https://geo.fcc.gov/api/census/block/find"


@dataclass
class Location:
    # Variables required on object instantiation
    street: str
    apt_num: str
    city: str
    state: str
    zipcode: str
    census_year: int

    # Geographic coordinates
    latitude: float | None = None
    longitude: float | None = None

    # US Census FIPS code
    fips: str = ""

    # ADI info
    # Maps ADI versions for THIS location to a tuple of 2 strings:
    #   {"ADI version": ("ADI state ranking", "ADI national ranking")}
    # Example:
    #   {"CA_v3.2": (4, 4), "US_v4_0_1": (3, 2)}
    adi_data: dict[str:tuple] = field(default_factory=dict)

    def get_full_address(self) -> str:
        """Returns a string containing the full address of this Location.
        This string is composed of multiple attributes, and not all attributes are guaranteed to be present,
        so sequences of double spaces "  " may occur where an empty attribute is found.
        """
        return " ".join([self.street, self.apt_num, self.city, self.state, self.zipcode])

    def can_geocode(self) -> bool:
        """Returns True if a Location is eligible for geocoding.
        A Location is eligible for geocoding if:
        (1) all 3 of its street, city, and state fields are not empty,
        (2) the Location's address is not a Military Mail address, and
        (3) the Location's address is not a PO box
        """
        _street_upper = self.street.upper()
        _city_upper = self.city.upper()
        _state_upper = self.state.upper()

        # https://www.usps.com/ship/apo-fpo-dpo.htm
        is_military_address = (
            any([i for i in _MILITARY_MAIL_POST_OFFICE if i in _city_upper])
            or _state_upper in _MILITARY_MAIL_STATES
            or "PSC " in _street_upper
        )

        street_has_po_box = any([i for i in _PO_BOX_CHECKS if i in _street_upper])

        return (
            len(self.street) > 0
            and len(self.city) > 0
            and len(self.state) > 0
            and not is_military_address
            and not street_has_po_box
        )

    def get_latlong(self, geocoder: GoogleV3) -> tuple[float]:
        """Sets the latitude and longitude coordinates for this Location.
        Returns the coordinates as a tuple: (latitude, longitude)
        Coordinate data is provided by the Google Maps Geocoding API."""
        if self.can_geocode():
            try:
                full_address = self.get_full_address()
                time.sleep(0.5 + random.random())  # rate limiting
                # THE API CALL:
                location_query_result = geocoder.geocode(query=full_address)
                if location_query_result is None:
                    # If the geocode returns no results, try again without the address number
                    alternate_address = full_address.lstrip(DIGITS)
                    print(f"        Attempting alternate address '{alternate_address}'")
                    # THE BACKUP API CALL:
                    location_query_result = geocoder.geocode(query=alternate_address)

                if location_query_result is not None:
                    # API call was successful
                    location_geometry = location_query_result.raw["geometry"]["location"]
                    self.latitude = location_geometry["lat"]
                    self.longitude = location_geometry["lng"]
                    return (self.latitude, self.longitude)
            except Exception as e:
                print(f"        Encountered an error with geocoding: {e}")
        else:
            print("This location's address is not eligible for geocoding")
        return ()

    def get_fips(self) -> str:
        """Sets the FIPS code for this Location.
        Returns the FIPS code as a string.
        FIPS data is provided by the US FCC Area API.
        """
        if self.latitude is None or self.longitude is None:
            print(
                "Cannot look up FIPS code: this location is missing latitude/longitude coordinates."
            )
            return ""
        # Census year specified in main.py
        url_params = urllib.parse.urlencode(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "censusYear": self.census_year,
                "format": "json",
            }
        )
        try:
            # print(f"        Requesting URL {url}?{params}")
            time.sleep(0.5 + random.random())  # rate limiting
            api_response = requests.get(url=FCC_API_URL, params=url_params)
            data = api_response.json()
            if isinstance(data, dict) and "Block" in data and "FIPS" in data["Block"]:
                fips_code = data["Block"]["FIPS"]
                if fips_code:
                    # API call was successful
                    self.fips = fips_code
                    return fips_code
                else:
                    # requests translates null JSON values to Python's None object
                    print("        FCC API returned nothing")
            else:
                print(
                    f"        Got data in an unexpected format from FCC API: {api_response.text}"
                )
        except Exception as e:
            print(f"        Encountered an error with FCC API call: {e}")
        return ""

    def get_adi(self, local_adi_file_data: list[tuple[str, dict]]) -> dict:
        """Sets the ADI version, state and national ranks for this Location.
        Returns the ranks as a dict mapping ADI version to a tuple of rankings: {"ver": ("state", "national"), ... }
        Due to some ranks not being valid integers, the rankings are stored as strings.
        (See "Suppression Codes" in the ADI data's accompanying .txt file for more details.)
        """
        if len(self.fips) == 0:
            print("Cannot look up ADI score: this location is missing a FIPS code.")
            return dict()
        for adi_sheet in local_adi_file_data:
            loaded_adi_version = adi_sheet[0]
            loaded_adi_data = adi_sheet[1]

            # ADI data expects 12-digit FIPS codes for lookup
            # FIPS data is not guaranteed to be 12 chars long; FCC API usually provides 15-char codes but could be 14 chars long
            fips_for_lookup = self.fips
            match len(fips_for_lookup):
                case 12:
                    pass
                case 14:
                    # print(
                    #     "        14-char FIPS: Adding a leading 0 and truncating to 12 chars for ADI lookup only"
                    # )
                    fips_for_lookup = f"0{fips_for_lookup}"[:12]
                case 15:
                    # print(
                    #     "        15-char FIPS: Truncating to 12 chars for ADI lookup only"
                    # )
                    fips_for_lookup = fips_for_lookup[:12]
                case _:
                    print(
                        f"        Invalid FIPS length: {len(fips_for_lookup)} (expected 12-, 14-, or 15-char long FIPS code)"
                    )
                    return ()
            if fips_for_lookup in loaded_adi_data:
                self.adi_data[loaded_adi_version] = loaded_adi_data[fips_for_lookup]
        return self.adi_data

    def prep_for_output(self) -> list[dict]:
        """Returns a list of dictionaries, with each dictionary being a row to be written to the
        final CSV file.
        One row will be written per ADI lookup (multiple ADI lookups can occur if multiple ADI
        spreadsheets are placed in the "adi-data" folder).
        """
        location_data_dict = asdict(self)
        del location_data_dict["adi_data"]
        result = []
        for adi_version in self.adi_data:
            # Create a copy of location_data_dict and add these keys:
            # "adi_version","adi_state","adi_national" (one per ADI source file)
            one_row_data = copy(location_data_dict)
            one_row_data["adi_version"] = adi_version
            one_row_data["adi_state"] = self.adi_data[adi_version][0]
            one_row_data["adi_national"] = self.adi_data[adi_version][1]
            result.append(one_row_data)
        return result
