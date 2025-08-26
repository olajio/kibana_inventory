import sys
import requests
import logging
import json
from argparse import ArgumentParser
from datetime import datetime
import pytz


# Set up timestamp in EST
def set_timestamp():
    """Sets up a log file with the creation timestamp in its name using EST time."""
    # Define the EST timezone
    est_tz = pytz.timezone("US/Eastern")

    # Get the current timestamp in EST
    timestamp = datetime.now(est_tz).strftime("%Y_%m_%d_%H_%M_%S")
    return timestamp

# Setup Log file
def setup_log_file(timestamp):
    """Creates a log file name with the EST timestamp."""
    log_file_name = f"log_file_{timestamp}.log"
    return log_file_name


# Configures logging to redirect logs and print statements to a custom log file
def setup_logging(log_file="output.log"):
    """
    Configures logging to redirect logs and print statements to a custom log file.
    Overwrites the log file on each run.

    Args:
        log_file (str): The name of the log file.
    """
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),  # Overwrite log file each run
            logging.StreamHandler(sys.stdout),  # Print logs to stdout
        ],
    )

    # Redirect print statements to logging
    sys.stdout = LoggerWriter(logging.getLogger(), logging.INFO)
    sys.stderr = LoggerWriter(logging.getLogger(), logging.ERROR)


class LoggerWriter:
    """
    A file-like object to redirect print statements to the logging system.

    Args:
        logger (logging.Logger): Logger instance to write to.
        log_level (int): Logging level for the messages.
    """
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level

    def write(self, message):
        if message.strip():  # Ignore empty messages
            self.logger.log(self.log_level, message.strip())

    def flush(self):
        pass  # No action needed for flush


# Set up headers for Kibana authentication
def get_headers(api_key):
    """
    Generates the necessary headers for Kibana API authentication.
    """
    headers = {
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {api_key}'
    }
    return headers


def get_all_spaces(kibana_url, headers):
    """
    Retrieves all Kibana spaces using the Kibana Spaces API.
    Returns a list of space objects.
    """
    spaces_endpoint = f"{kibana_url}/api/spaces/space"
    logging.info("Retrieving all Kibana spaces...")
    try:
        response = requests.get(spaces_endpoint, headers=headers, verify=True)
        response.raise_for_status()
        spaces = response.json()
        logging.info(f"Successfully retrieved {len(spaces)} Kibana spaces.")
        return spaces
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve Kibana spaces. Error: {e}")
        return []


def find_object_by_id(kibana_url, headers, space_id, object_id):
    """
    Searches for a specific saved object by its ID within a given space.

    Args:
        kibana_url (str): The base URL of the Kibana instance.
        headers (dict): The authorization headers.
        space_id (str): The ID of the space to search in.
        object_id (str): The ID of the saved object to find.

    Returns:
        dict: The saved object dictionary if found, otherwise None.
    """
    find_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
    params = {
        'search': object_id,
        'search_fields': 'id',
        'per_page': 1  # Only need one result
    }

    try:
        response = requests.get(find_endpoint, headers=headers, params=params, verify=True)
        response.raise_for_status()
        data = response.json()
        saved_objects = data.get("saved_objects", [])
        
        # Filter for an exact match on ID, as the search can be fuzzy
        for obj in saved_objects:
            if obj.get('id') == object_id:
                return obj
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to search for object '{object_id}' in space '{space_id}'. Error: {e}")
        return None


def main(kibana_url, api_key, object_id):
    """
    Main function to orchestrate the search for a specific object across all spaces.
    """
    timestamp = set_timestamp()
    log_file_name = setup_log_file(timestamp)
    setup_logging(log_file_name)

    headers = get_headers(api_key)
    spaces = get_all_spaces(kibana_url, headers)
    
    if not spaces:
        logging.warning("No spaces found or failed to retrieve spaces. Exiting.")
        return

    object_found = False
    for space in spaces:
        space_id = space.get("id")
        space_name = space.get("name")
        
        if not space_id:
            continue

        logging.info(f"Searching for object '{object_id}' in space: '{space_name}'...")
        found_object = find_object_by_id(kibana_url, headers, space_id, object_id)

        if found_object:
            object_title = found_object.get("attributes", {}).get("title", "N/A")
            object_type = found_object.get("type", "N/A")
            
            logging.info(
                "\n✅ Object Found!"
                "\n------------------------------------------------------------"
                f"\n  Object Title: {object_title}"
                f"\n  Object Type: {object_type}"
                f"\n  Space Name: {space_name} (ID: {space_id})"
                "\n------------------------------------------------------------"
            )
            object_found = True
            break # Exit the loop once the object is found

    if not object_found:
        logging.warning(f"\n❌ Object with ID '{object_id}' was not found in any Kibana space.")


if __name__ == "__main__":
    parser = ArgumentParser(description='Finds a specific Kibana object by ID across all spaces.')
    parser.add_argument('--kibana_url', required=True, help='The URL of your Kibana instance.')
    parser.add_argument('--api_key', required=True, help='The Kibana API key with appropriate permissions.')
    parser.add_argument('--object_id', required=True, help='The ID of the saved object to find.')

    args = parser.parse_args()
    main(args.kibana_url, args.api_key, args.object_id)
