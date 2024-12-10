import os
import boto3
from typing import Dict, Tuple
from boto3.dynamodb.types import TypeDeserializer

dynamodb = boto3.client('dynamodb')
deserializer = TypeDeserializer()

def get_entity_info(component_id: str) -> Tuple[str, str, str]:
    """Get workspace, path, and component names for a given component ID."""
    
    # Get component info
    component = get_item(os.environ['COMPONENT_TABLE'], component_id)
    if not component:
        raise ValueError(f"Component {component_id} not found")
    
    # Get path info
    path = get_item(os.environ['PATH_TABLE'], component['path_id'])
    if not path:
        raise ValueError(f"Path {component['path_id']} not found")
    
    # Get workspace info
    workspace = get_item(os.environ['WORKSPACE_TABLE'], path['workspace_id'])
    if not workspace:
        raise ValueError(f"Workspace {path['workspace_id']} not found")
    
    return workspace['name'], path['name'], component['name']

def get_item(table_name: str, item_id: str) -> Dict:
    """Get item from DynamoDB table."""
    response = dynamodb.get_item(
        TableName=table_name,
        Key={'id': {'S': item_id}}
    )
    
    if 'Item' not in response:
        return None
        
    return {k: deserializer.deserialize(v) for k, v in response['Item'].items()}

def format_s3_key(workspace_name: str, path_name: str, component_name: str, data_id: str) -> str:
    """Format S3 key according to the specified pattern."""
    return f"{workspace_name}/{path_name}/{component_name}/{data_id}.parquet"
