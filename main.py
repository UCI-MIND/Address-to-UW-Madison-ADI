import csv
import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from geopy.geocoders import GoogleV3

from Location import Location

# Used to look up FIPS codes
CENSUS_YEAR = 2020

# Script settings
THIS_DIRECTORY = Path(__file__).parent
ADDRESSES_FILE = "addresses.csv"
SECRETS_FILE = "secrets.json"
ADI_DATA_FOLDER = "adi-data"

# Used in loading data from ADI spreadsheet
_GISJOIN_REGEX = re.compile("^G([0-9]{2})0([0-9]{3})0([0-9]{7})$")


def json_to_dict(json_filepath: Path) -> dict:
    if not json_filepath.is_file():
        with open(json_filepath, "w+") as outfile:
            print("Secrets file not found.")
            outfile.write("""{
    "google_cloud_api_key": "YOUR_API_KEY_HERE"
}""")
            print(
                f"A template secrets file has been created at this location:\n\t{json_filepath.resolve()}\nPlease open this file in a text editor to provide your Google Cloud API key for geocoding."
            )
        exit(1)
    with open(json_filepath) as infile:
        return json.load(infile)


def load_addresses() -> list[Location]:
    locations = []
    address_file_path = Path(THIS_DIRECTORY, ADDRESSES_FILE)
    if not address_file_path.is_file():
        print("Address file not found.")
        with open(address_file_path, "w+") as outfile:
            outfile.write("street,apt_num,city,state,zip")
        print(
            f"A template address file has been created at this location:\n\t{address_file_path.resolve()}\nPlease open this file in a text or spreadsheet editor to provide addresses to this script."
        )
        exit(1)
    with open(address_file_path, "r+") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            locations.append(
                Location(
                    row["street"],
                    row["apt_num"],
                    row["city"],
                    row["state"],
                    row["zip"],
                    CENSUS_YEAR,
                )
            )
    return locations


def _gisjoin_to_fips(gisjoin: str) -> str:
    """Converts a GISJOIN string to a standard FIPS code."""
    # Example GISJOIN string:
    # G01000100208032
    # _SS_CCC_xxxxxxx

    # _ = padding char that we don't want (0 or "G")
    # SS = state
    # CCC = county
    # xxxxxxx = all the rest

    # 12-char FIPS code = SSCCCxxxxxxx
    parsed_groups = _GISJOIN_REGEX.search(gisjoin).groups()
    if (
        len(parsed_groups) == 3
        and len(parsed_groups[0]) == 2
        and len(parsed_groups[1]) == 3
        and len(parsed_groups[2]) == 7
    ):
        return "".join(parsed_groups)
    print(f"Failed to convert GISJOIN {gisjoin} to FIPS")
    return ""


def load_adi_data() -> list[tuple[str, dict]]:
    """Reads CSV files of ADI data downloaded from the Wisconsin Neighborhood Atlas project.
    Returns a list containing 1 2-tuple per ADI spreadsheet file. Each 2-tuple contains:
        1. A string containing the CSV file's name (to keep track of ADI version)
        2. A dict that maps all 12-digit FIPS codes in that file to a tuple of each code's
           STATE rank and NATIONAL rank (in order!)
    Example:
        [(
            "CA_2020_v3.2",                     # Name of .csv file from https://www.neighborhoodatlas.medicine.wisc.edu/
            {
                "131210101212": ("1", "2"),     # ranked #1 in CA, #2 in the nation
                "060014013002": ("GQ", "GQ"),
                ...
            }
        ),
        (
            "US_2022_v4_0_1",
            {
                "180670007001": ("4", "64"),
                "721519900000": ("PH", "PH"),
                "131210101212": ("QDI", "QDI"),
                ...
            }
        ), ...]
    Assumes the following columns exist in the ADI CSV files:
        "GISJOIN" (but prioritizes "FIPS" if that column exists)
        "ADI_STATERNK"
        "ADI_NATRANK"
    This function will need further development if newer ADI releases have different types of
    data or column names.
    """
    adi_downloads_folder_path = Path(THIS_DIRECTORY, ADI_DATA_FOLDER)
    if not adi_downloads_folder_path.is_dir():
        print("ADI data folder not found.")
        adi_downloads_folder_path.mkdir()
        print(
            f"A folder has been created at this location:\n\t{adi_downloads_folder_path.resolve()}\nPlease download your desired ADI data and place the files in this folder. Refer to README.md for more details."
        )
        exit(1)

    adi_downloads_csvs = [f for f in adi_downloads_folder_path.iterdir() if f.suffix == ".csv"]
    # if len(adi_downloads_csvs) != 1:
    #     print(f"Expected only 1 ADI CSV file (found {len(adi_downloads_csvs)})")
    #     return [("", dict())]

    result = []
    for adi_file in adi_downloads_csvs:
        with open(adi_file) as infile:
            # print(f"- Reading local ADI file '{adi_file.name}'")
            adi_version_str = adi_file.stem
            fips_to_adi_ranks = dict()
            reader = csv.DictReader(infile)
            csv_has_gisjoin_only = (
                "GISJOIN" in reader.fieldnames and "FIPS" not in reader.fieldnames
            )

            for row in reader:
                # How data should be stored in fips_to_adi_ranks: fips_to_adi_ranks[fips] = (state, national)
                fips = _gisjoin_to_fips(row["GISJOIN"]) if csv_has_gisjoin_only else row["FIPS"]
                fips_to_adi_ranks[fips] = (row["ADI_STATERNK"], row["ADI_NATRANK"])
        result.append((adi_version_str, fips_to_adi_ranks))
    return result


def write_output_csv(data: list[Location]) -> Path:
    if len(data) < 1:
        return Path()
    new_csv_file = Path(
        THIS_DIRECTORY, f"addresses-output-{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    field_names = list(asdict(data[0]).keys())
    field_names.remove("adi_data")
    field_names.extend(["adi_version", "adi_state", "adi_national"])
    with open(new_csv_file, "w+", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=field_names, lineterminator="\n")
        writer.writeheader()
        for location in data:
            for row in location.prep_for_output():
                writer.writerow(row)
    return new_csv_file.resolve()


def main() -> None:
    print("Starting....")
    locations = load_addresses()
    if len(locations) == 0:
        return
    print(f"Got {len(locations)} address(es)")

    # Pre-load shared resources for all addresses
    secrets = json_to_dict(Path(THIS_DIRECTORY, SECRETS_FILE))
    if "google_cloud_api_key" not in secrets:
        return
    main_geocoder = GoogleV3(secrets["google_cloud_api_key"])
    adi_files_data = load_adi_data()
    if len(adi_files_data) == 0:
        return
    print(f"Got {len(adi_files_data)} ADI file(s)")

    for i, location in enumerate(locations, start=1):
        print(f"Address {i}/{len(locations)}:")
        print("    Getting latitude/longitude coords....")
        location.get_latlong(main_geocoder)
        print("    Getting FIPS code....")
        location.get_fips()
        print("    Looking up ADI rankings....")
        location.get_adi(adi_files_data)
    file_written = write_output_csv(locations)
    print(f"Wrote data to CSV file:\n    {file_written}")
    print("Done!")
    return


if __name__ == "__main__":
    main()
