import os
import json
import boto3
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
from boto3.dynamodb.conditions import Key
from ...lib.common_utils import setup_logging, generate_id

logger = setup_logging(__name__)
dynamodb = boto3.resource('dynamodb')


def get_admin_user(email: str) -> str:
    """Get existing user or fail."""
    user_table = dynamodb.Table(os.environ['USER_TABLE'])

    logger.info(f"Looking for user with email: {email}")
    try:
        # Check for existing user
        users = user_table.scan(
            FilterExpression='#email = :email',
            ExpressionAttributeNames={'#email': 'email'},
            ExpressionAttributeValues={':email': email}
        )

        # logger.info(f"Scan result: {json.dumps(users)}")

        if not users['Items']:
            logger.error(f"No user found with email {email}")
            raise Exception(f"Admin user with email {email} not found. Please create the user first.")

        user_id = users['Items'][0]['id']
        logger.info(f"Found user with ID: {user_id}")
        return user_id

    except Exception as e:
        logger.error(f"Error in get_admin_user: {str(e)}")
        raise

def get_or_create_workspace(user_id: str, workspace_name: str) -> Tuple[str, bool]:
    """
    Get existing workspace or create new one with account.
    If workspace exists, verify user is admin, otherwise fail.
    If workspace doesn't exist, create it and make user admin.
    """
    workspace_table = dynamodb.Table(os.environ['WORKSPACE_TABLE'])
    account_table = dynamodb.Table(os.environ['ACCOUNT_TABLE'])

    # Check for existing workspace by name
    workspaces = workspace_table.scan(
        FilterExpression='#name = :name',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={':name': workspace_name}
    )

    if workspaces['Items']:
        # Workspace exists, verify user is admin
        workspace = workspaces['Items'][0]
        accounts = account_table.query(
            IndexName='UserWorkspaceIndex',
            KeyConditionExpression=Key('user_id').eq(user_id) & Key('workspace_id').eq(workspace['id'])
        )

        if not accounts['Items']:
            raise Exception(f"User is not associated with workspace '{workspace_name}'")

        # Check if user is admin
        if not accounts['Items'][0]['user_is_workspace_admin']:
            raise Exception(f"User is not an admin of workspace '{workspace_name}'")

        return workspace['id'], False

    # Workspace doesn't exist, create it and make user admin
    workspace_id = create_workspace(workspace_name)
    account_id = create_account(user_id, workspace_id, True)  # Always create as admin

    return workspace_id, True

def get_or_create_path(workspace_id: str, path_name: str) -> Tuple[str, bool]:
    """Get existing path or create new one."""
    path_table = dynamodb.Table(os.environ['PATH_TABLE'])

    normalized_name = path_name.lower().replace(' ', '-')

    # Check for existing path using the GSI directly
    # No need for FilterExpression since both workspace_id and normalized_name are part of the index
    try:
        response = path_table.query(
            IndexName='WorkspacePathIndex',
            KeyConditionExpression='workspace_id = :ws_id AND normalized_name = :norm_name',
            ExpressionAttributeValues={
                ':ws_id': workspace_id,
                ':norm_name': normalized_name
            }
        )

        if response['Items']:
            return response['Items'][0]['id'], False

        # Create new path if not found
        path_id = generate_id('path')

        path_table.put_item(Item={
            'id': path_id,
            'workspace_id': workspace_id,
            'name': path_name,
            'normalized_name': normalized_name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': '{}'
        })

        return path_id, True

    except Exception as e:
        logger.error(f"Error in get_or_create_path: {str(e)}")
        raise


def get_or_create_component(workspace_id: str, path_id: str, component_name: str) -> Tuple[str, bool]:
    """Get existing component or create new one."""
    component_table = dynamodb.Table(os.environ['COMPONENT_TABLE'])

    # Use the GSI directly with KeyConditionExpression
    try:
        response = component_table.query(
            IndexName='PathComponentIndex',
            KeyConditionExpression='path_id = :path_id AND #name = :name',
            ExpressionAttributeNames={
                '#name': 'name'
            },
            ExpressionAttributeValues={
                ':path_id': path_id,
                ':name': component_name
            }
        )

        if response['Items']:
            return response['Items'][0]['id'], False

        # Create new component
        component_id = generate_id('comp')

        component_table.put_item(Item={
            'id': component_id,
            'workspace_id': workspace_id,
            'path_id': path_id,
            'name': component_name,
            'has_data': True,
            'has_action': False,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': '{}'
        })

        return component_id, True

    except Exception as e:
        logger.error(f"Error in get_or_create_component: {str(e)}")
        raise

def create_workspace(name: str) -> str:
    """Create a new workspace."""
    workspace_table = dynamodb.Table(os.environ['WORKSPACE_TABLE'])
    workspace_id = generate_id('ws')
    
    workspace_table.put_item(Item={
        'id': workspace_id,
        'name': name,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'metadata': '{}'
    })
    
    return workspace_id

def create_account(user_id: str, workspace_id: str, is_admin: bool) -> str:
    """Create a new account."""
    account_table = dynamodb.Table(os.environ['ACCOUNT_TABLE'])
    account_id = generate_id('acc')

    account_table.put_item(Item={
        'id': account_id,
        'user_id': user_id,
        'workspace_id': workspace_id,
        'user_is_workspace_admin': is_admin,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    })
    
    return account_id

def create_path(workspace_id: str, name: str, normalized_name: str) -> str:
    """Create a new path."""
    path_table = dynamodb.Table(os.environ['PATH_TABLE'])
    path_id = generate_id('path')

    path_table.put_item(Item={
        'id': path_id,
        'workspace_id': workspace_id,
        'name': name,
        'normalized_name': normalized_name,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'metadata': '{}'
    })
    
    return path_id

def create_component(workspace_id: str, path_id: str, name: str) -> str:
    """Create a new component."""
    component_table = dynamodb.Table(os.environ['COMPONENT_TABLE'])
    component_id = generate_id('comp')
    
    component_table.put_item(Item={
        'id': component_id,
        'workspace_id': workspace_id,
        'path_id': path_id,
        'name': name,
        'has_data': True,
        'has_action': False,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'metadata': '{}'
    })
    
    return component_id

def create_data_entries(component_id: str, data_events: List[Dict], add_to_data_lake: bool) -> List[str]:
    """Create multiple data entries."""
    data_table = dynamodb.Table(os.environ['DATA_TABLE'])
    created_ids = []
    
    for event in data_events:
        data_id = generate_id('data')
        
        data_table.put_item(Item={
            'id': data_id,
            'component_id': component_id,
            'data': event['data'],
            'data_map': event.get('dataMap', '{}'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'addToDataLake': add_to_data_lake
        })
        
        created_ids.append(data_id)
    
    return created_ids

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle bulk data creation with workspace/path/component hierarchy."""
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        input_data = event.get('arguments', {}).get('input', {})
        if not input_data:
            logger.error("No input data found in event")
            raise Exception("No input data provided")

        # Validate required fields
        required_fields = ['admin_email', 'workspace_name', 'path_name', 'component_name', 'data']
        missing_fields = [field for field in required_fields if field not in input_data]
        if missing_fields:
            raise Exception(f"Missing required fields: {', '.join(missing_fields)}")

        user_id = get_admin_user(input_data['admin_email'])
        logger.info(f"Found user: {user_id}")

        # Get or create workspace and related entities
        workspace_id, workspace_created = get_or_create_workspace(
            user_id,
            input_data['workspace_name']
        )
        logger.info(f"Workspace processed: {workspace_id}, created: {workspace_created}")

        path_id, path_created = get_or_create_path(
            workspace_id,
            input_data['path_name']
        )
        logger.info(f"Path processed: {path_id}, created: {path_created}")

        component_id, component_created = get_or_create_component(
            workspace_id,
            path_id,
            input_data['component_name']
        )
        logger.info(f"Component processed: {component_id}, created: {component_created}")

        # Create all data entries
        created_data_ids = create_data_entries(
            component_id,
            input_data['data'],
            input_data.get('addToDataLake', True)
        )
        logger.info(f"Created data entries: {created_data_ids}")

        result = {
            'workspace_id': workspace_id,
            'path_id': path_id,
            'component_id': component_id,
            'created_data_ids': created_data_ids,
            'workspace_created': workspace_created,
            'path_created': path_created,
            'component_created': component_created
        }

        logger.info(f"Returning result: {json.dumps(result)}")
        return result

    except Exception as e:
        logger.error(f"Error in bulk data creation: {str(e)}", exc_info=True)
        # Important: Re-raise the error to ensure AppSync gets an error response
        raise
