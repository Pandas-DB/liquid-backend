import os
import json
import requests
from typing import Dict, Any
from datetime import datetime

class AppSyncClient:
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key
        }

    def execute_query(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        payload = {
            'query': query,
            'variables': variables or {}
        }
        response = requests.post(self.api_url, json=payload, headers=self.headers)
        return response.json()

def test_workspace_flow():
    # Initialize client - replace with your values
    client = AppSyncClient(
        api_url="YOUR_APPSYNC_API_URL",
        api_key="YOUR_API_KEY"
    )

    # Create workspace
    create_workspace_query = """
    mutation CreateWorkspace($name: String!, $metadata: AWSJSON) {
        createWorkspace(name: $name, metadata: $metadata) {
            id
            name
            created_at
        }
    }
    """
    workspace_response = client.execute_query(
        create_workspace_query,
        {
            "name": "Test Workspace",
            "metadata": json.dumps({"description": "Test workspace"})
        }
    )
    workspace_id = workspace_response['data']['createWorkspace']['id']
    print(f"Created workspace: {workspace_id}")

    # Create path
    create_path_query = """
    mutation CreatePath($workspaceId: ID!, $name: String!, $metadata: AWSJSON) {
        createPath(workspaceId: $workspaceId, name: $name, metadata: $metadata) {
            id
            name
            normalized_name
        }
    }
    """
    path_response = client.execute_query(
        create_path_query,
        {
            "workspaceId": workspace_id,
            "name": "Test Path",
            "metadata": json.dumps({"description": "Test path"})
        }
    )
    path_id = path_response['data']['createPath']['id']
    print(f"Created path: {path_id}")

    # Create component
    create_component_query = """
    mutation CreateComponent($pathId: ID!, $name: String!, $hasData: Boolean!, $hasAction: Boolean!, $metadata: AWSJSON) {
        createComponent(
            pathId: $pathId,
            name: $name,
            hasData: $hasData,
            hasAction: $hasAction,
            metadata: $metadata
        ) {
            id
            name
        }
    }
    """
    component_response = client.execute_query(
        create_component_query,
        {
            "pathId": path_id,
            "name": "Test Component",
            "hasData": True,
            "hasAction": False,
            "metadata": json.dumps({"type": "test"})
        }
    )
    component_id = component_response['data']['createComponent']['id']
    print(f"Created component: {component_id}")

    # Create data
    create_data_query = """
    mutation CreateData($componentId: ID!, $data: AWSJSON!, $dataMap: AWSJSON!, $addToDataLake: Boolean) {
        createData(
            componentId: $componentId,
            data: $data,
            dataMap: $dataMap,
            addToDataLake: $addToDataLake
        ) {
            id
            s3_location
        }
    }
    """
    data_response = client.execute_query(
        create_data_query,
        {
            "componentId": component_id,
            "data": json.dumps({"value": "test data"}),
            "dataMap": json.dumps({"type": "string"}),
            "addToDataLake": True
        }
    )
    data_id = data_response['data']['createData']['id']
    print(f"Created data: {data_id}")

    # List workspaces
    list_workspaces_query = """
    query ListWorkspaces($limit: Int) {
        listWorkspaces(limit: $limit) {
            items {
                id
                name
                paths {
                    items {
                        id
                        name
                        components {
                            items {
                                id
                                name
                                data {
                                    items {
                                        id
                                        s3_location
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    workspaces = client.execute_query(
        list_workspaces_query,
        {"limit": 10}
    )
    print("\nWorkspace hierarchy:")
    print(json.dumps(workspaces, indent=2))

    # Clean up (optional)
    delete_queries = {
        "data": """
        mutation DeleteData($id: ID!) {
            deleteData(id: $id)
        }
        """,
        "component": """
        mutation DeleteComponent($id: ID!) {
            deleteComponent(id: $id)
        }
        """,
        "path": """
        mutation DeletePath($id: ID!) {
            deletePath(id: $id)
        }
        """,
        "workspace": """
        mutation DeleteWorkspace($id: ID!) {
            deleteWorkspace(id: $id)
        }
        """
    }

    # Uncomment to test deletion
    """
    for entity_type, query in delete_queries.items():
        entity_id = locals()[f"{entity_type}_id"]
        response = client.execute_query(query, {"id": entity_id})
        print(f"Deleted {entity_type}: {entity_id}")
    """

if __name__ == "__main__":
    test_workspace_flow()
