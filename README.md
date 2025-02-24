# Address-to-UW-Madison-ADI
Obtains Area Deprivation Index (ADI) scores for US addresses

# Overview

This script uses a 4-step procedure to obtain ADI scores for US addresses:

1. Load addresses
    * Utilizes a local spreadsheet file (filled out by you)
2. Obtain latitude/longitude coordinates for each address
    * Utilizes the [Google Maps Geocoding API](https://developers.google.com/maps/documentation/geocoding/overview)
3. Use each address's latitude/longitude coordinates to look up its corresponding US Census FIPS code
    * Utilizes the free & public [US FCC Block API](https://geo.fcc.gov/api/census/#!/block/get_block_find)
4. Use each address's FIPS code to look up its ADI scores
    * Utilizes pre-downloaded CSV files from the [University of Wisconsin, Madison Neighborhood Atlas](https://www.neighborhoodatlas.medicine.wisc.edu/)

# Prerequisites

## Python environment

This script was written using [Python 3.12](https://www.python.org/downloads/). UCI MIND does not guarantee that it will work on older Python versions.

We highly recommend using a [virtual environment](https://docs.python.org/3/library/venv.html) to run this script, as it relies on some third-party Python packages. After cloning the repository, open a terminal window in the repository's root folder and run the following commands to prepare your virtual environment:

```
# Create a Python virtual environment (only need to do this once):
python -m venv .venv

# Activate the virtual environment:
# (Windows: .ps1 for PowerShell or .bat for Command Prompt)
.\.venv\Scripts\Activate.ps1

# If using PowerShell and "running scripts is disabled on this system", need to enable running
# external scripts. Open PowerShell as admin and use this command (only need to do this once):
set-executionpolicy remotesigned

# While in the virtual env, upgrade pip and install packages (only need to do these once):
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Notes on other supporting files

The files `pyproject.toml` and `.vscode\settings.json` were used in the development process for this script. They provide settings for automatic code formatting using [VS Code's](https://code.visualstudio.com/) [Ruff extension](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff). You can safely ignore these files if they do not apply to your dev environment.

* If you have Python programmers on your team, they can learn more about Ruff here: https://docs.astral.sh/ruff/

## Addresses

Addresses are expected to be in a spreadsheet file named **`addresses.csv`** located in the same folder as `main.py`. This file contains all the addresses that will be queried for latitude/longitude coordinate data, FIPS codes, and ADI rankings, with one address per row. Running the script once will automatically create this file, but you can just as easily create one yourself with a simple text editor. `addresses.csv` should contain these column headers:

```
street,apt_num,city,state,zip
```

Then, populate the sheet with addresses as you see fit using your favorite spreadsheet program or text editor.

## Google Maps API key

To fetch latitude and longitude coordinates, this script requires a **Google Cloud API Key** that is attached to an account with the **Google Maps Geocoding API** enabled, which requires a credit card. The Geocoding API is in the "Essentials" level, and as of March 1, 2025, Google only offers "Essential" APIs **10,000 free calls per month**. Be mindful of this limit if you don't want to receive a bill from Google later!

* Sources:
  * https://mapsplatform.google.com/pricing/
  * https://developers.google.com/maps/billing-and-pricing/pricing?hl=en#geocoding
  * https://mapsplatform.google.com/resources/blog/build-more-for-free-and-access-more-discounts-online-with-google-maps-platform-updates/

This API key should be stored in a file called **`secrets.json`**, also located in the same folder as `main.py`. Running the script once will automatically create this file, but you can just as easily create one yourself with a simple text editor. `secrets.json` should follow this format:

```
{
    "google_cloud_api_key": "YOUR_API_KEY_HERE"
}
```

## US Census year

By default, this script queries for FIPS codes from the most recent US Census (2020 as of writing). If you're running this script in the future (or if you're running retrospective studies), the variable `CENSUS_YEAR` near the top of the file `main.py` must be changed so the correct FIPS codes can be requested. Refer to the [FCC Area API documentation](https://geo.fcc.gov/api/census/#!/block/get_block_find) for more info.

This should be set to align with the version(s) of the ADI dataset(s) you wish to use.

## ADI data

Download your desired ADI datasets from the [Neighborhood Atlas website](https://www.neighborhoodatlas.medicine.wisc.edu/download). Select these options: **12-digit FIPS codes**, **All States**, and your desired year/version.

* If you know all your addresses are within a specific state, feel free to select the option for that state instead of "All States".

Your download should be a .zip file containing 1 .txt and 1 .csv file. Place the .csv file in a folder named `adi-data` in the same folder as `main.py`. Running the script once will create this folder for you, or you can create it yourself.

You can place multiple .csv files from the Neighborhood Atlas in the `adi-data` folder (different versions, different years, etc.) and the script will look up and report ADI scores from all of them in the results.

---

The folder `adi-data` and files `secrets.json` and `addresses.csv` are untracked in this Git repository due to containing information specific to you.

# Running the script

Once you have your addresses, Google API key, and ADI data, you can run the script in a terminal. Assuming you set up a virtual environment using the steps above, the script can be ran with these commands in this repository's root directory:

```
# Activate your virtual environment (assuming your terminal is PowerShell on Windows)
.\.venv\Scripts\Activate.ps1

python main.py

# Just to be tidy
deactivate
```

The script will process each address one-at-a-time. When complete, each address and all associated location data will be written to a resultant CSV file with a timestamp for manual review.

We encourage programmers to modify this script to better integrate into their tech stack. For example, instead of using manually-edited CSVs for input, you can use an API of your own to fetch location data from your study.

# Funding

To support our work and ensure future opportunities for development, please acknowledge the software and funding.
The project was funded by The University of California, Irvine's Institute for Memory Impairments and Neurological Disorders (UCI MIND) grant, P30AG066519.
