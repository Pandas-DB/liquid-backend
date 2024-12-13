def get_path_components(workspace_id: str, path_id: str, limit: int = 20, next_token: Optional[str] = None) -> Dict[
    str, Any]:
    """Get paginated components for a path."""
    component_table = dynamodb.Table(os.environ['COMPONENT_TABLE'])

    query_params = {
        'IndexName': 'PathComponentIndex',
        'KeyConditionExpression': 'path_id = :pid',
        'FilterExpression': 'workspace_id = :wid',
        'ExpressionAttributeValues': {
            ':pid': path_id,
            ':wid': workspace_id
        },
        'Limit': limit
    }

    if next_token:
        query_params['ExclusiveStartKey'] = eval(next_token)

    response = component_table.query(**query_params)

    return {
        'items': response.get('Items', []),
        'next_token': str(response['LastEvaluatedKey']) if 'LastEvaluatedKey' in response else None
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle request for path components."""
    try:
        logger.info(f"Received event: {event}")

        # Get parameters
        user_id = event.get('user_id')
        workspace_id = event.get('workspace_id')
        path_id = event.get('path_id')
        limit = event.get('limit', 20)
        next_token = event.get('next_token')

        # Validate input
        if not all([user_id, workspace_id, path_id]):
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

        # Get components
        result = get_path_components(workspace_id, path_id, limit, next_token)

        return {
            'statusCode': 200,
            'body': result
        }

    except Exception as e:
        logger.error(f"Error in get_path_components: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f"Internal error: {str(e)}"
        }
