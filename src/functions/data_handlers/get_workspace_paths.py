# src/functions/data_handlers/get_workspace_paths.py

import os
import boto3
import logging
from typing import Dict, Any, Optional, List
from boto3.dynamodb.conditions import Key
from ...lib.common_utils import setup_logging

logger = setup_logging(__name__)
dynamodb = boto3.resource('dynamodb')


def check_workspace_access(user_id: str, workspace_id: str) -> bool:
    """Verify if user has access to workspace."""
    account_table = dynamodb.Table(os.environ['ACCOUNT_TABLE'])

    response = account_table.query(
        IndexName='UserWorkspaceIndex',
        KeyConditionExpression='user_id = :uid AND workspace_id = :wid',
        ExpressionAttributeValues={
            ':uid': user_id,
            ':wid': workspace_id
        }
    )

    return bool(response['Items'])


def get_workspace_paths(workspace_id: str, limit: int = 20, next_token: Optional[str] = None) -> Dict[str, Any]:
    """Get paginated paths for a workspace."""
    path_table = dynamodb.Table(os.environ['PATH_TABLE'])

    query_params = {
        'IndexName': 'WorkspacePathIndex',
        'KeyConditionExpression': 'workspace_id = :wid',
        'ExpressionAttributeValues': {':wid': workspace_id},
        'Limit': limit
    }

    if next_token:
        query_params['ExclusiveStartKey'] = eval(next_token)  # Convert string token to dict

    response = path_table.query(**query_params)

    return {
        'items': response.get('Items', []),
        'next_token': str(response['LastEvaluatedKey']) if 'LastEvaluatedKey' in response else None
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle request for workspace paths."""
    try:
        logger.info(f"Received event: {event}")

        # Get parameters
        user_id = event.get('user_id')
        workspace_id = event.get('workspace_id')
        limit = event.get('limit', 20)
        next_token = event.get('next_token')

        # Validate input
        if not all([user_id, workspace_id]):
            return {
                'statusCode': 400,
                'body': 'Missing required parameters'
            }

        # Check access
        if not check_workspace_access(user_id, workspace_id):
            return {
                'statusCode': 403,
                'body': 'Not authorized to access this workspace'
            }

        # Get paths
        result = get_workspace_paths(workspace_id, limit, next_token)

        return {
            'statusCode': 200,
            'body': result
        }

    except Exception as e:
        logger.error(f"Error in get_workspace_paths: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f"Internal error: {str(e)}"
        }
