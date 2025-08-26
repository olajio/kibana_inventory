import sys
import requests
import logging
import json
from argparse import ArgumentParser
from datetime import datetime
import pytz
import os

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
    # Create the log file name with the EST timestamp
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


def list_kibana_objects_in_space(kibana_url, headers, space_id):
    """
    Lists all saved objects in a specific Kibana space, handling pagination.
    Returns a list of object dictionaries with their type and ID.
    """
    objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
    all_objects = []
    page = 1
    per_page = 1000

    object_types = ["config", "config-global", "url", "index-pattern", "action", "query", "tag", "graph-workspace",
                    "alert", "search", "visualization", "event-annotation-group", "dashboard", "lens", "cases",
                    "metrics-data-source", "links", "canvas-element", "canvas-workpad", "osquery-saved-query",
                    "osquery-pack", "csp-rule-template", "map", "infrastructure-monitoring-log-view",
                    "threshold-explorer-view", "uptime-dynamic-settings", "synthetics-privates-locations", "apm-indices",
                    "infrastructure-ui-source", "inventory-view", "infra-custom-dashboards", "metrics-explorer-view",
                    "apm-service-group", "apm-custom-dashboards", "timelion-sheet"]

    for obj_type in object_types:
        while True:
            params = {
                'type': obj_type,
                'per_page': per_page,
                'page': page,
            }
            try:
                response = requests.get(objects_endpoint, headers=headers, params=params, verify=True)
                response.raise_for_status()
                data = response.json()
                objects = data.get("saved_objects", [])
                all_objects.extend([{"id": obj["id"], "type": obj["type"]} for obj in objects])

                if data.get('total', 0) <= page * per_page:
                    break
                page += 1
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to retrieve {obj_type} objects for space '{space_id}'. Error: {e}")
                break

    return all_objects


def main(kibana_url, api_key):
    """
    Main function to orchestrate the retrieval and listing of all Kibana objects.
    """
    timestamp = set_timestamp()
    log_file_name = setup_log_file(timestamp)
    setup_logging(log_file_name)

    headers = get_headers(api_key)
    spaces = get_all_spaces(kibana_url, headers)
    
    if not spaces:
        logging.warning("No spaces found or failed to retrieve spaces. Exiting.")
        return

    all_kibana_objects_by_space = {}
    for space in spaces:
        space_id = space.get("id")
        space_name = space.get("name")
        if not space_id:
            continue

        logging.info(f"\n--- Listing objects in space: '{space_name}' (ID: {space_id}) ---")
        objects_in_space = list_kibana_objects_in_space(kibana_url, headers, space_id)
        
        if objects_in_space:
            all_kibana_objects_by_space[space_id] = objects_in_space
            logging.info(f"Found {len(objects_in_space)} Kibana objects in space '{space_name}'.")
        else:
            logging.info(f"No objects found in space '{space_name}'.")

    # Pretty print the final result to the log file and console
    logging.info("\n--- Final Summary: All Kibana Objects by Space ---")
    if all_kibana_objects_by_space:
        logging.info(json.dumps(all_kibana_objects_by_space, indent=2))
    else:
        logging.warning("No objects were found in any space.")

if __name__ == "__main__":
    parser = ArgumentParser(description='Loops through all Kibana spaces and lists all saved objects.')
    parser.add_argument('--kibana_url', required=True, help='The URL of your Kibana instance.')
    parser.add_argument('--api_key', required=True, help='The Kibana API key with appropriate permissions.')

    args = parser.parse_args()
    main(args.kibana_url, args.api_key)
