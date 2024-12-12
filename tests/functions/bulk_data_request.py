""" with curl:

curl -X POST \
  'YOUR_APPSYNC_ENDPOINT' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: YOUR_API_KEY' \
  -d '{
    "query": "mutation BulkCreateData($input: BulkDataInput!) { bulkCreateData(input: $input) { workspace_id path_id component_id created_data_ids workspace_created path_created component_created } }",
    "variables": {
      "input": {
        "workspace_name": "my-workspace",
        "path_name": "my-path",
        "component_name": "my-component",
        "data": [
          {
            "data": "{\"value\": \"test1\"}",
            "dataMap": "{\"type\": \"string\"}"
          },
          {
            "data": "{\"value\": \"test2\"}",
            "dataMap": "{\"type\": \"string\"}"
          }
        ],
        "addToDataLake": true
      }
    }
  }'
"""

from os import getenv
import requests
import json

def bulk_create_data(api_endpoint: str, api_key: str, workspace_name: str, path_name: str, 
                    component_name: str, data_events: list, add_to_data_lake: bool = True):
    """
    Send bulk data creation request to AppSync API
    
    Args:
        api_endpoint: Your AppSync API endpoint
        api_key: Your AppSync API key
        workspace_name: Name of the workspace
        path_name: Name of the path
        component_name: Name of the component
        data_events: List of data events to create
        add_to_data_lake: Whether to add data to S3
    """
    
    # GraphQL query
    query = """
    mutation BulkCreateData($input: BulkDataInput!) {
        bulkCreateData(input: $input) {
            workspace_id
            path_id
            component_id
            created_data_ids
            workspace_created
            path_created
            component_created
        }
    }
    """
    
    # Variables for the query
    variables = {
        "input": {
            "workspace_name": workspace_name,
            "path_name": path_name,
            "component_name": component_name,
            "data": data_events,
            "addToDataLake": add_to_data_lake
        }
    }
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }
    
    # Request payload
    payload = {
        'query': query,
        'variables': variables
    }
    
    # Make the request
    try:
        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes
        
        result = response.json()
        
        # Check for errors in the response
        if 'errors' in result:
            raise Exception(f"GraphQL Errors: {json.dumps(result['errors'], indent=2)}")
            
        return result['data']['bulkCreateData']
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Your AppSync configuration
    API_ENDPOINT = getenv('API_ENDPOINT')
    API_KEY = getenv('API_KEY')
    
    # Example data events
    data_events = [
        {
            "data": json.dumps({"value": "test1"}),
            "dataMap": json.dumps({"type": "string"})
        },
        {
            "data": json.dumps({"value": "test2"}),
            "dataMap": json.dumps({"type": "string"})
        }
    ]
    
    try:
        result = bulk_create_data(
            api_endpoint=API_ENDPOINT,
            api_key=API_KEY,
            workspace_name="my-workspace",
            path_name="my-path",
            component_name="my-component",
            data_events=data_events,
            add_to_data_lake=True
        )
        
        print("Bulk data creation successful!")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Failed to create bulk data: {str(e)}")
