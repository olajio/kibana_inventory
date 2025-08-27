# Kibana Objects Inventory Script

A comprehensive Python script for managing and inventorying Kibana objects across multiple deployments and spaces. This script allows you to search for specific objects, generate complete inventories, and export results in multiple formats.

## Features

- 🔍 **Multi-Deployment Support**: Pre-configured support for prod, qa, dev, mon, infosec, and ccs deployments
- 🏢 **Multi-Space Inventory**: Automatically scans all Kibana spaces
- 🔎 **Object Search**: Find specific objects by ID across all spaces
- 📊 **Multiple Export Formats**: JSON, CSV, and formatted table outputs
- 📋 **Comprehensive Object Types**: Supports dashboards, visualizations, data views, lenses, maps, and more
- 📝 **Detailed Logging**: Timestamped logs with deployment information
- 🔄 **Backward Compatible**: Supports both new deployment-based and legacy URL/API key approaches
- 🔧 **Debug Mode**: Advanced debugging capabilities to troubleshoot object structure and field extraction issues
- ✅ **Robust Field Extraction**: Enhanced algorithms to properly extract titles and descriptions from Kibana objects

## Supported Object Types

- **Dashboards**
- **Visualizations** 
- **Data Views** (Index Patterns)
- **Saved Searches**
- **Lenses**
- **Canvas Workpads**
- **Maps**
- **Graph Workspaces**
- **Alerts**
- **Cases**
- **Tags**
- **Links**
- And many more...

## Prerequisites

### Python Dependencies
```bash
pip install requests pytz
```

### Required Permissions
- Kibana API access with read permissions
- Access to all spaces you want to inventory
- Valid API keys for each deployment

## Configuration

### Deployment Configuration
The script includes pre-configured deployment mappings. Update the `deployment_config` dictionary with your actual endpoints and API keys:

```python
deployment_config = {
    "prod": {
        "kibana_url": "https://your-prod-kibana-url",
        "api_key": "your_prod_api_key"
    },
    "qa": {
        "kibana_url": "https://your-qa-kibana-url", 
        "api_key": "your_qa_api_key"
    },
    # ... additional deployments
}
```

## Usage

### Deployment-Based Usage (Recommended)

#### Search for Specific Object
```bash
# Search for an object in production
python kibana_inventory.py --deployment prod --object_id your_object_id

# Search in QA environment
python kibana_inventory.py --deployment qa --object_id dashboard-123
```

#### Generate Complete Inventory
```bash
# Generate table format inventory for production
python kibana_inventory.py --deployment prod

# Generate JSON export for development
python kibana_inventory.py --deployment dev --output_format json

# Generate all formats with detailed view
python kibana_inventory.py --deployment qa --output_format all --detailed

# Custom output filename
python kibana_inventory.py --deployment prod --output_file my_inventory

# Debug mode to troubleshoot object structure
python kibana_inventory.py --deployment prod --debug
```

### Legacy Usage (Direct URL/API Key)
```bash
# Legacy approach - still supported
python kibana_inventory.py --kibana_url https://your-kibana-url --api_key your_api_key --object_id your_object_id
```

## Command Line Arguments

### Primary Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `--deployment` | Deployment name (prod, qa, dev, mon, infosec, ccs) | Yes* |
| `--kibana_url` | Direct Kibana URL (legacy mode) | Yes* |
| `--api_key` | Direct API key (legacy mode) | Yes* |

*Either `--deployment` OR both `--kibana_url` and `--api_key` are required

### Optional Arguments
| Argument | Description | Default |
|----------|-------------|---------|
| `--object_id` | Search for specific object ID across all spaces | None |
| `--output_format` | Output format: json, csv, table, all | table |
| `--detailed` | Show detailed inventory with all object information | False |
| `--output_file` | Base filename for output files (without extension) | Auto-generated |
| `--debug` | Enable debug mode to show object structure details | False |

## Output Files

### File Naming Convention
- **Logs**: `kibana_inventory_{deployment}_log_{timestamp}.log`
- **Inventory**: `kibana_inventory_{deployment}_{timestamp}.{format}`
- **Search Results**: `{filename}_{deployment}_search_results.json`

### Output Formats

#### Table Format (Default)
- Console-formatted summary and detailed tables
- Space-by-space breakdown
- Object type summaries

#### JSON Format
```json
{
  "space_id": {
    "space_name": "Space Name",
    "space_id": "space_id", 
    "total_objects": 150,
    "objects_by_type": {
      "dashboard": [...],
      "visualization": [...]
    },
    "type_counts": {
      "dashboard": 25,
      "visualization": 40
    }
  }
}
```

#### CSV Format
Flat CSV file with columns:
- Space ID
- Space Name  
- Object Type
- Object ID
- Object Title
- Description
- Updated At

## Examples

### Common Use Cases

#### 1. Find a Dashboard Across All Environments
```bash
# Check production
python kibana_inventory.py --deployment prod --object_id dashboard-analytics-2024

# Check QA
python kibana_inventory.py --deployment qa --object_id dashboard-analytics-2024
```

#### 2. Generate Weekly Inventory Reports
```bash
# Production inventory
python kibana_inventory.py --deployment prod --output_format all --output_file weekly_prod_inventory

# QA inventory
python kibana_inventory.py --deployment qa --output_format json --output_file weekly_qa_inventory
```

#### 3. Audit All Objects in Development
```bash
python kibana_inventory.py --deployment dev --detailed --output_format csv
```

#### 4. Debug Object Structure Issues
```bash
# Enable debug mode to see object structure and field extraction
python kibana_inventory.py --deployment prod --object_id your_object_id --debug

# Debug mode for inventory generation (shows first few objects)
python kibana_inventory.py --deployment qa --debug
```

## Error Handling

The script includes comprehensive error handling for:
- Invalid deployment names
- Network connectivity issues
- Authentication failures
- Missing spaces or objects
- File I/O errors

All errors are logged with timestamps and detailed information.

## Logging

### Log Features
- **Timestamped entries** in EST timezone
- **Deployment-specific** log files
- **Dual output** to console and file
- **Different log levels** (INFO, ERROR, WARNING)

### Log File Location
Logs are created in the same directory as the script with the format:
```
kibana_inventory_{deployment}_log_{YYYY_MM_DD_HH_MM_SS}.log
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors
```
Failed to retrieve spaces. Error: 401
```
**Solution**: Verify your API key has the correct permissions and is valid.

#### 2. Unknown Deployment Error
```
Unknown deployment: staging
Available deployments: prod, qa, dev, mon, infosec, ccs
```
**Solution**: Use one of the available deployments or add your deployment to the configuration.

#### 3. No Objects Found
```
❌ No objects found with ID: your-object-id
```
**Solution**: 
- Verify the object ID is correct
- Check if you have access to all necessary spaces
- Ensure the object exists in the specified deployment

#### 4. Network Connection Issues
```
Failed to retrieve spaces. Error: Connection timeout
```
**Solution**:
- Check network connectivity
- Verify the Kibana URL is accessible
- Check for firewall or proxy issues

#### 5. Missing Titles or Descriptions (Shows "N/A")
```
Object titles showing as "N/A" or "Dashboard-object-id"
```
**Solution**:
- Use `--debug` flag to inspect object structure
- Check the debug output for actual field locations
- Verify objects have titles in Kibana UI

### Debug Mode

The script includes comprehensive debugging capabilities to help troubleshoot issues:

#### Enable Debug Mode
```bash
# Debug specific object search
python kibana_inventory.py --deployment prod --object_id your_object_id --debug

# Debug inventory generation (shows first few objects from each type)
python kibana_inventory.py --deployment qa --debug --output_format table
```

#### Debug Output Example
```
=== DEBUG: Object Structure for dashboard in space default ===
Object ID: 8249c8c0-6070-11ec-8a8a-e5fb1e2cdc19
Object Type: dashboard
Top-level keys: ['attributes', 'coreMigrationVersion', 'id', 'managed', ...]
Attributes keys: ['description', 'hits', 'kibanaSavedObjectMeta', 'title', ...]
attributes.title: 'PR Dashboard' (FOUND)
attributes.description: '' (EMPTY/NOT FOUND)
✅ EXTRACTED TITLE: 'PR Dashboard'
✅ EXTRACTED DESCRIPTION: ''
=== END DEBUG ===
```

### Debug Tips

1. **Use debug mode first** when encountering issues with object titles or descriptions
2. **Check logs** for detailed error information and object structure details
3. **Verify deployment configuration** matches your actual endpoints
4. **Test connectivity** to Kibana URL manually
5. **Validate API key permissions** in Kibana UI
6. **Run with minimal arguments** first to test basic connectivity
7. **Check object structure** if titles appear as "N/A" or fallback names

## Security Considerations

- **API Keys**: Store API keys securely and rotate regularly
- **Access Control**: Ensure script users have appropriate Kibana permissions
- **Log Security**: Protect log files as they may contain sensitive information
- **Network Security**: Use HTTPS endpoints only

## Script Flowchart

The following flowchart illustrates the script's execution flow:

```
                                       +----------------+
                                       |  Start Script  |
                                       | (Parse Args)   |
                                       +----------------+
                                                |
                                                v
                                       +------------------------+
                                       | Validate Arguments     |
                                       | & Deployment Config    |
                                       +------------------------+
                                                    |
                                                    v
                                       +------------+--------------+
                                       | Valid Args | Invalid Args |
                                       +------------+--------------+
                                             |                   |        
                                             v                   v
                                       +----------------+   +------------------------+
                                       | Setup Logging  |   | Show Error Message     |
                                       | & Auth Headers |   | & Exit Script          |
                                       +----------------+   +------------------------+
                                               |            
                                               v            
                                       +------------------------+
                                       |   Determine Mode       |
                                       | (Search vs Inventory)  |
                                       +------------------------+
                                                    |
                                                    v
                                       +------------+------------+
                                       | Search Mode| Inventory  |
                                       | (Object ID)| Mode       |
                                       +------------+------------+
                                                 |            |
                                                 v            v
                                       +----------------+   +------------------------+
                                       | Get All Spaces |   | Get All Spaces         |
                                       | Search Each    |   | For Each Space:        |
                                       | for Object ID  |   | - Get Saved Objects    |
                                       +----------------+   | - Get Data Views       |
                                               |            | - Combine & Organize   |
                                               v            +------------------------+
                                       +------------------------+        |
                                       | Display Search Results |        v
                                       | (Found/Not Found)      |   +------------------------+
                                       +------------------------+   |  Generate Output       |
                                               |                    |  Based on Format       |
                                               v                    | (JSON/CSV/Table/All)   |
                                       +------------------------+   +------------------------+
                                       | Export Search Results  |        |
                                       | to JSON (if requested) |        v
                                       +------------------------+   +------------------------+
                                               |                    |  Export Files &        |
                                               +--------------------+  Display Results       |
                                               |                    +------------------------+
                                               v
                                       +------------------------+
                                       |     Log Completion     |
                                       |     & Exit Script      |
                                       +------------------------+
```



## Support

For issues or questions:
1. Check the troubleshooting section
2. Review log files for detailed error information
3. Verify your deployment configuration
4. Contact your Kibana administrator for permission issues
