#!/usr/bin/env python3
"""
Kibana Objects Inventory Script

This script loops through all Kibana spaces and lists all Kibana objects 
including data views, dashboards, saved searches, visualizations, and lenses
with their corresponding IDs in each space.

Usage:
    python kibana_inventory.py --kibana_url https://your-kibana-url --api_key your_api_key [--output_format json|csv|table]
"""

import sys
import requests
import logging
import json
import csv
from collections import defaultdict
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
    # Create the log file name with the EST timestamp
    log_file_name = f"kibana_inventory_log_{timestamp}.log"
    return log_file_name


# Configures logging to redirect logs and print statements to a custom log file
def setup_logging(log_file="kibana_inventory_output.log"):
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
    headers = {
        'kbn-xsrf': 'true',
        'Content-Type': 'application/json',
        'Authorization': f'ApiKey {api_key}'
    }
    return headers


# Get all Kibana spaces
def get_all_spaces(headers, kibana_url):
    """
    Retrieve all Kibana spaces.
    
    Args:
        headers (dict): Headers for Kibana authentication
        kibana_url (str): Kibana base URL
        
    Returns:
        list: List of space objects
    """
    logging.info("Retrieving all Kibana spaces...")
    spaces_endpoint = f"{kibana_url}/api/spaces/space"
    
    try:
        response = requests.get(spaces_endpoint, headers=headers, verify=True)
        response.raise_for_status()
        
        spaces = response.json()
        logging.info(f"Found {len(spaces)} spaces")
        return spaces
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve spaces. Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response: {e.response.text}")
        return []


# Retrieve specific types of Kibana objects in a space
def get_kibana_objects_by_type(headers, kibana_url, space_id, object_types):
    """
    Retrieve Kibana objects of specific types in a given space.
    
    Args:
        headers (dict): Headers for Kibana authentication
        kibana_url (str): Kibana base URL
        space_id (str): Space ID to search in
        object_types (list): List of object types to retrieve
        
    Returns:
        list: List of Kibana objects with their details
    """
    logging.info(f"Retrieving Kibana objects in space: '{space_id}'...")
    find_objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
    
    all_objects = []
    
    for obj_type in object_types:
        params = {
            'type': obj_type,
            'per_page': 10000,
            'fields': 'title,description,updated_at'
        }
        
        try:
            response = requests.get(find_objects_endpoint, headers=headers, params=params, verify=True)
            response.raise_for_status()
            
            data = response.json()
            objects = data.get("saved_objects", [])
            
            for obj in objects:
                object_info = {
                    "space_id": space_id,
                    "id": obj["id"],
                    "type": obj["type"],
                    "title": obj.get("attributes", {}).get("title", "N/A"),
                    "description": obj.get("attributes", {}).get("description", ""),
                    "updated_at": obj.get("updated_at", "N/A")
                }
                all_objects.append(object_info)
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to retrieve {obj_type} objects in space {space_id}. Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response: {e.response.text}")
    
    return all_objects


# Get data views using the data views API
def get_data_views(headers, kibana_url, space_id):
    """
    Get all data views in a specific space using the data views API.
    
    Args:
        headers (dict): Headers for Kibana authentication
        kibana_url (str): Kibana base URL
        space_id (str): Space ID to search in
        
    Returns:
        list: List of data view objects
    """
    logging.info(f"Retrieving data views in space: '{space_id}'...")
    dataview_url = f'{kibana_url}/s/{space_id}/api/data_views'
    
    try:
        response = requests.get(dataview_url, headers=headers, verify=True)
        response.raise_for_status()
        
        data = response.json()
        data_views = data.get('data_view', [])
        
        formatted_data_views = []
        for dv in data_views:
            data_view_info = {
                "space_id": space_id,
                "id": dv["id"],
                "type": "data-view",
                "title": dv.get("title", "N/A"),
                "description": dv.get("name", ""),
                "updated_at": "N/A"
            }
            formatted_data_views.append(data_view_info)
            
        return formatted_data_views
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve data views in space {space_id}. Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response: {e.response.text}")
        return []


# Generate inventory report for all spaces
def generate_kibana_inventory(headers, kibana_url):
    """
    Generate a complete inventory of Kibana objects across all spaces.
    
    Args:
        headers (dict): Headers for Kibana authentication
        kibana_url (str): Kibana base URL
        
    Returns:
        dict: Complete inventory organized by space
    """
    # Object types to inventory
    object_types = [
        "dashboard", "visualization", "search", "lens", 
        "canvas-workpad", "map", "graph-workspace"
    ]
    
    # Get all spaces
    spaces = get_all_spaces(headers, kibana_url)
    if not spaces:
        logging.error("No spaces found or unable to retrieve spaces")
        return {}
    
    inventory = {}
    total_objects = 0
    
    for space in spaces:
        space_id = space["id"]
        space_name = space.get("name", space_id)
        
        logging.info(f"Processing space: {space_name} (ID: {space_id})")
        
        # Get saved objects
        saved_objects = get_kibana_objects_by_type(headers, kibana_url, space_id, object_types)
        
        # Get data views separately
        data_views = get_data_views(headers, kibana_url, space_id)
        
        # Combine all objects
        all_objects = saved_objects + data_views
        
        # Organize by type
        objects_by_type = defaultdict(list)
        for obj in all_objects:
            objects_by_type[obj["type"]].append(obj)
        
        inventory[space_id] = {
            "space_name": space_name,
            "space_id": space_id,
            "total_objects": len(all_objects),
            "objects_by_type": dict(objects_by_type),
            "type_counts": {obj_type: len(objects) for obj_type, objects in objects_by_type.items()}
        }
        
        total_objects += len(all_objects)
        logging.info(f"Found {len(all_objects)} objects in space '{space_name}'")
    
    logging.info(f"Inventory complete! Total objects across all spaces: {total_objects}")
    return inventory


# Export inventory to JSON
def export_to_json(inventory, filename):
    """Export inventory to JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False)
        logging.info(f"Inventory exported to JSON: {filename}")
    except Exception as e:
        logging.error(f"Failed to export to JSON: {e}")


# Export inventory to CSV
def export_to_csv(inventory, filename):
    """Export inventory to CSV file."""
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Space ID', 'Space Name', 'Object Type', 'Object ID', 
                'Object Title', 'Description', 'Updated At'
            ])
            
            # Write data
            for space_id, space_data in inventory.items():
                space_name = space_data["space_name"]
                
                for obj_type, objects in space_data["objects_by_type"].items():
                    for obj in objects:
                        writer.writerow([
                            space_id, space_name, obj_type, obj["id"],
                            obj["title"], obj["description"], obj["updated_at"]
                        ])
        
        logging.info(f"Inventory exported to CSV: {filename}")
    except Exception as e:
        logging.error(f"Failed to export to CSV: {e}")


# Print inventory summary table
def print_summary_table(inventory):
    """Print a summary table of the inventory."""
    print("\n" + "="*80)
    print("KIBANA OBJECTS INVENTORY SUMMARY")
    print("="*80)
    
    # Summary by space
    print(f"{'Space Name':<25} {'Space ID':<15} {'Total Objects':<15}")
    print("-" * 55)
    
    total_across_all = 0
    for space_id, space_data in inventory.items():
        space_name = space_data["space_name"][:24]  # Truncate long names
        total_objects = space_data["total_objects"]
        total_across_all += total_objects
        
        print(f"{space_name:<25} {space_id:<15} {total_objects:<15}")
    
    print("-" * 55)
    print(f"{'TOTAL':<25} {'':<15} {total_across_all:<15}")
    
    # Object type summary across all spaces
    print("\n" + "="*60)
    print("OBJECT TYPE SUMMARY (All Spaces)")
    print("="*60)
    
    type_totals = defaultdict(int)
    for space_data in inventory.values():
        for obj_type, count in space_data["type_counts"].items():
            type_totals[obj_type] += count
    
    print(f"{'Object Type':<25} {'Total Count':<15}")
    print("-" * 40)
    
    for obj_type, count in sorted(type_totals.items()):
        print(f"{obj_type:<25} {count:<15}")
    
    print("\n" + "="*80)


# Print detailed inventory
def print_detailed_inventory(inventory):
    """Print detailed inventory with all objects."""
    print("\n" + "="*100)
    print("DETAILED KIBANA OBJECTS INVENTORY")
    print("="*100)
    
    for space_id, space_data in inventory.items():
        space_name = space_data["space_name"]
        total_objects = space_data["total_objects"]
        
        print(f"\nSPACE: {space_name} (ID: {space_id}) - {total_objects} objects")
        print("-" * 80)
        
        if total_objects == 0:
            print("  No objects found in this space")
            continue
        
        for obj_type, objects in space_data["objects_by_type"].items():
            print(f"\n  {obj_type.upper()} ({len(objects)} objects):")
            
            for obj in objects:
                title = obj["title"][:50] + "..." if len(obj["title"]) > 50 else obj["title"]
                print(f"    • ID: {obj['id']}")
                print(f"      Title: {title}")
                if obj["description"]:
                    desc = obj["description"][:60] + "..." if len(obj["description"]) > 60 else obj["description"]
                    print(f"      Description: {desc}")
                print()


# Search for a specific object ID across all spaces
def search_object_by_id(headers, kibana_url, target_object_id):
    """
    Search for a specific object ID across all Kibana spaces.
    
    Args:
        headers (dict): Headers for Kibana authentication
        kibana_url (str): Kibana base URL
        target_object_id (str): The object ID to search for
        
    Returns:
        list: List of matching objects with their details
    """
    logging.info(f"Searching for object ID: {target_object_id} across all spaces...")
    
    # Get all spaces first
    spaces = get_all_spaces(headers, kibana_url)
    if not spaces:
        logging.error("No spaces found or unable to retrieve spaces")
        return []
    
    matching_objects = []
    
    # Object types to search through
    object_types = [
        "dashboard", "visualization", "search", "lens", 
        "canvas-workpad", "map", "graph-workspace",
        "index-pattern", "config", "url", "action", 
        "query", "tag", "alert", "event-annotation-group",
        "cases", "metrics-data-source", "links", 
        "canvas-element", "osquery-saved-query",
        "osquery-pack", "csp-rule-template",
        "infrastructure-monitoring-log-view",
        "threshold-explorer-view", "uptime-dynamic-settings",
        "synthetics-privates-locations", "apm-indices",
        "infrastructure-ui-source", "inventory-view",
        "infra-custom-dashboards", "metrics-explorer-view",
        "apm-service-group", "apm-custom-dashboards"
    ]
    
    for space in spaces:
        space_id = space["id"]
        space_name = space.get("name", space_id)
        
        logging.info(f"Searching in space: {space_name} (ID: {space_id})")
        
        # Search through saved objects
        find_objects_endpoint = f"{kibana_url}/s/{space_id}/api/saved_objects/_find"
        
        for obj_type in object_types:
            try:
                params = {
                    'type': obj_type,
                    'per_page': 10000,
                    'fields': 'title,description,updated_at'
                }
                
                response = requests.get(find_objects_endpoint, headers=headers, params=params, verify=True)
                response.raise_for_status()
                
                data = response.json()
                objects = data.get("saved_objects", [])
                
                for obj in objects:
                    if obj["id"] == target_object_id:
                        object_info = {
                            "space_id": space_id,
                            "space_name": space_name,
                            "id": obj["id"],
                            "type": obj["type"],
                            "title": obj.get("attributes", {}).get("title", "N/A"),
                            "description": obj.get("attributes", {}).get("description", ""),
                            "updated_at": obj.get("updated_at", "N/A"),
                            "created_at": obj.get("created_at", "N/A"),
                            "version": obj.get("version", "N/A")
                        }
                        matching_objects.append(object_info)
                        logging.info(f"Found matching object in space '{space_name}'!")
                        
            except requests.exceptions.RequestException as e:
                logging.warning(f"Failed to search {obj_type} in space {space_id}: {e}")
        
        # Also search data views using the data views API
        try:
            dataview_url = f'{kibana_url}/s/{space_id}/api/data_views'
            response = requests.get(dataview_url, headers=headers, verify=True)
            response.raise_for_status()
            
            data = response.json()
            data_views = data.get('data_view', [])
            
            for dv in data_views:
                if dv["id"] == target_object_id:
                    object_info = {
                        "space_id": space_id,
                        "space_name": space_name,
                        "id": dv["id"],
                        "type": "data-view",
                        "title": dv.get("title", "N/A"),
                        "description": dv.get("name", ""),
                        "updated_at": "N/A",
                        "created_at": "N/A",
                        "version": "N/A"
                    }
                    matching_objects.append(object_info)
                    logging.info(f"Found matching data view in space '{space_name}'!")
                    
        except requests.exceptions.RequestException as e:
            logging.warning(f"Failed to search data views in space {space_id}: {e}")
    
    return matching_objects


# Display search results
def display_search_results(matching_objects, target_object_id):
    """
    Display the search results in a formatted manner.
    
    Args:
        matching_objects (list): List of matching object details
        target_object_id (str): The object ID that was searched for
    """
    print("\n" + "="*80)
    print(f"SEARCH RESULTS FOR OBJECT ID: {target_object_id}")
    print("="*80)
    
    if not matching_objects:
        print(f"❌ No objects found with ID: {target_object_id}")
        print("The object may not exist or you may not have access to the spaces containing it.")
        return
    
    print(f"✅ Found {len(matching_objects)} matching object(s):")
    print()
    
    for i, obj in enumerate(matching_objects, 1):
        print(f"{i}. OBJECT DETAILS:")
        print(f"   Object ID: {obj['id']}")
        print(f"   Object Type: {obj['type']}")
        print(f"   Title/Name: {obj['title']}")
        print(f"   Space ID: {obj['space_id']}")
        print(f"   Space Name: {obj['space_name']}")
        
        if obj['description']:
            desc = obj['description'][:100] + "..." if len(obj['description']) > 100 else obj['description']
            print(f"   Description: {desc}")
        
        if obj['updated_at'] != "N/A":
            print(f"   Last Updated: {obj['updated_at']}")
        if obj['created_at'] != "N/A":
            print(f"   Created: {obj['created_at']}")
        if obj['version'] != "N/A":
            print(f"   Version: {obj['version']}")
        
        print("-" * 60)
    
    if len(matching_objects) > 1:
        print(f"⚠️  WARNING: Found {len(matching_objects)} objects with the same ID across different spaces!")
        print("   This may indicate duplicate objects or cross-space references.")


def main():
    parser = ArgumentParser(description='Search for Kibana objects by ID across all spaces or generate inventory')
    parser.add_argument('--kibana_url', required=True, help='Kibana URL (e.g., https://your-kibana-url)')
    parser.add_argument('--api_key', required=True, help='Kibana API key for authentication')
    parser.add_argument('--object_id', help='Search for a specific object ID across all spaces')
    parser.add_argument('--output_format', choices=['json', 'csv', 'table', 'all'], default='table',
                       help='Output format for inventory (default: table)')
    parser.add_argument('--detailed', action='store_true', 
                       help='Show detailed inventory with all object details')
    parser.add_argument('--output_file', help='Base filename for output files (without extension)')
    
    args = parser.parse_args()
    
    # Get timestamp and setup logging
    timestamp = set_timestamp()
    log_file_name = setup_log_file(timestamp)
    setup_logging(log_file_name)
    
    # Setup authentication headers
    headers = get_headers(args.api_key)
    
    # Check if we're searching for a specific ID
    if args.object_id:
        logging.info(f"Starting search for object ID: {args.object_id}")
        matching_objects = search_object_by_id(headers, args.kibana_url, args.object_id)
        display_search_results(matching_objects, args.object_id)
        
        # Optionally export search results to JSON
        if matching_objects and args.output_file:
            search_results = {
                "object_id": args.object_id,
                "timestamp": timestamp,
                "total_matches": len(matching_objects),
                "matches": matching_objects
            }
            
            output_filename = f"{args.output_file}_search_results.json"
            try:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(search_results, f, indent=2, ensure_ascii=False)
                logging.info(f"Search results exported to: {output_filename}")
            except Exception as e:
                logging.error(f"Failed to export search results: {e}")
        
        logging.info("Search completed!")
        return 0
    
    # If no search ID provided, generate full inventory
    logging.info("Starting Kibana objects inventory...")
    inventory = generate_kibana_inventory(headers, args.kibana_url)
    
    if not inventory:
        logging.error("Failed to generate inventory")
        return 1
    
    # Determine output filename base
    if args.output_file:
        output_base = args.output_file
    else:
        output_base = f"kibana_inventory_{timestamp}"
    
    # Export in requested format(s)
    if args.output_format in ['json', 'all']:
        export_to_json(inventory, f"{output_base}.json")
    
    if args.output_format in ['csv', 'all']:
        export_to_csv(inventory, f"{output_base}.csv")
    
    if args.output_format in ['table', 'all']:
        print_summary_table(inventory)
        
        if args.detailed:
            print_detailed_inventory(inventory)
    
    logging.info("Inventory generation completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
