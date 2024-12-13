"""Run example:
python3 scripts/queries/get_component_data.py comp-20241212083321 --aws-profile test --stage dev --limit 10

With curl:
curl -X POST \
  'YOUR_APPSYNC_ENDPOINT' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: YOUR_API_KEY' \
  -d '{
    "query": "query GetComponentData($componentId: ID!, $limit: Int, $nextToken: String) { listData(componentId: $componentId, limit: $limit, nextToken: $nextToken) { items { id component_id workspace_id data data_map s3_location created_at updated_at } nextToken } }",
    "variables": {
      "componentId": "comp-20241212083321",
      "limit": 10,
      "nextToken": null
    }
  }'
"""

#src/functions/data_handlers/get_component_data.py

def get_component_data(workspace_id: str, component_id: str, limit: int = 20, next_token: Optional[str] = None) -> Dict[
    str, Any]:
    """Get paginated data entries for a component."""
    data_table = dynamodb.Table(os.environ['DATA_TABLE'])

    query_params = {
        'IndexName': 'ComponentDataIndex',
        'KeyConditionExpression': 'component_id = :cid',
        'FilterExpression': 'workspace_id = :wid',
        'ExpressionAttributeValues': {
            ':cid': component_id,
            ':wid': workspace_id
        },
        'Limit': limit
    }

    if next_token:
        query_params['ExclusiveStartKey'] = eval(next_token)

    response = data_table.query(**query_params)

    return {
        'items': response.get('Items', []),
        'next_token': str(response['LastEvaluatedKey']) if 'LastEvaluatedKey' in response else None
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle request for component data."""
    try:
        logger.info(f"Received event: {event}")

        # Get parameters
        user_id = event.get('user_id')
        workspace_id = event.get('workspace_id')
        component_id = event.get('component_id')
        limit = event.get('limit', 20)
        next_token = event.get('next_token')

        # Validate input
        if not all([user_id, workspace_id, component_id]):
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

        # Get data
        result = get_component_data(workspace_id, component_id, limit, next_token)

        return {
            'statusCode': 200,
            'body': result
        }

    except Exception as e:
        logger.error(f"Error in get_component_data: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': f"Internal error: {str(e)}"
        }
