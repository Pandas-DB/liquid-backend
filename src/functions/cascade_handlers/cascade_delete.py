import os
import boto3
import logging
from typing import List, Dict, Any
from boto3.dynamodb.types import TypeDeserializer
from .utils import query_items, batch_delete
from ...lib.common_utils import setup_logging

logger = setup_logging(__name__)
dynamodb = boto3.client('dynamodb')
deserializer = TypeDeserializer()

def handler(event: Dict[str, Any], context: Any) -> None:
    """Handle DynamoDB Stream events for cascade deletion."""
    for record in event['Records']:
        try:
            # Only process REMOVE events
            if record['eventName'] != 'REMOVE':
                continue
                
            old_image = {k: deserializer.deserialize(v) for k, v in record['dynamodb']['OldImage'].items()}
            table_name = record['eventSourceARN'].split('/')[1]
            
            if table_name == 'workspace':
                delete_workspace_cascade(old_image['id'])
            elif table_name == 'path':
                delete_path_cascade(old_image['id'])
            elif table_name == 'component':
                delete_component_cascade(old_image['id'])
                
        except Exception as e:
            logger.error(f"Error processing delete cascade: {str(e)}", exc_info=True)
            raise

def delete_workspace_cascade(workspace_id: str) -> None:
    """Delete workspace and all related resources."""
    logger.info(f"Starting cascade delete for workspace {workspace_id}")
    
    try:
        # Delete accounts
        accounts = query_items('Account', 'WorkspaceUserIndex', 'workspace_id', workspace_id)
        if accounts:
            batch_delete(os.environ['ACCOUNT_TABLE'], accounts)
            logger.info(f"Deleted {len(accounts)} accounts for workspace {workspace_id}")
        
        # Delete paths and their components
        paths = query_items('Path', 'WorkspacePathIndex', 'workspace_id', workspace_id)
        for path in paths:
            delete_path_cascade(path['id'])
            
        logger.info(f"Completed cascade delete for workspace {workspace_id}")
        
    except Exception as e:
        logger.error(f"Error in workspace cascade delete: {str(e)}", exc_info=True)
        raise

def delete_path_cascade(path_id: str) -> None:
    """Delete path and all related components."""
    logger.info(f"Starting cascade delete for path {path_id}")
    
    try:
        components = query_items('Component', 'PathComponentIndex', 'path_id', path_id)
        for component in components:
            delete_component_cascade(component['id'])
            
        logger.info(f"Completed cascade delete for path {path_id}")
        
    except Exception as e:
        logger.error(f"Error in path cascade delete: {str(e)}", exc_info=True)
        raise

def delete_component_cascade(component_id: str) -> None:
    """Delete component and all related data."""
    logger.info(f"Starting cascade delete for component {component_id}")
    
    try:
        data_items = query_items('Data', 'ComponentDataIndex', 'component_id', component_id)
        if data_items:
            batch_delete(os.environ['DATA_TABLE'], data_items)
            logger.info(f"Deleted {len(data_items)} data items for component {component_id}")
            
    except Exception as e:
        logger.error(f"Error in component cascade delete: {str(e)}", exc_info=True)
        raise
