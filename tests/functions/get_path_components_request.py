"""Run example:
python3 scripts/queries/get_path_components_request.py path-20241212083321 --aws-profile test --stage dev --limit 10

With curl:
curl -X POST \
  'YOUR_APPSYNC_ENDPOINT' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: YOUR_API_KEY' \
  -d '{
    "query": "query GetPathComponents($pathId: ID!, $limit: Int, $nextToken: String) { listComponents(pathId: $pathId, limit: $limit, nextToken: $nextToken) { items { id name workspace_id path_id has_data has_action created_at updated_at metadata } nextToken } }",
    "variables": {
      "pathId": "path-20241212083321",
      "limit": 10,
      "nextToken": null
    }
  }'
"""


def get_path_components(api_endpoint: str, api_key: str, path_id: str,
                        limit: int = 20, next_token: str = None) -> dict:
    """
    Query components in a path with pagination
    """

    query = """
    query GetPathComponents($pathId: ID!, $limit: Int, $nextToken: String) {
        listComponents(pathId: $pathId, limit: $limit, nextToken: $nextToken) {
            items {
                id
                name
                workspace_id
                path_id
                has_data
                has_action
                created_at
                updated_at
                metadata
            }
            nextToken
        }
    }
    """

    variables = {
        "pathId": path_id,
        "limit": limit
    }

    if next_token:
        variables["nextToken"] = next_token

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    payload = {
        'query': query,
        'variables': variables
    }

    try:
        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()

        if 'errors' in result:
            raise Exception(f"GraphQL Errors: {json.dumps(result['errors'], indent=2)}")

        return result['data']['listComponents']

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Query data with pagination')
    parser.add_argument('id', help='ID to query (workspace_id, path_id, or component_id)')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--limit', type=int, default=20, help='Number of items per page')
    parser.add_argument('--next-token', help='Token for pagination')
    args = parser.parse_args()

    # Your AppSync configuration
    API_ENDPOINT = getenv('API_ENDPOINT')
    API_KEY = getenv('API_KEY')

    try:
        if not API_ENDPOINT or not API_KEY:
            raise ValueError("API_ENDPOINT and API_KEY environment variables must be set")

        print(f"Making request to: {API_ENDPOINT}")
        
        # Choose the appropriate function based on the script name
        if 'workspace_paths' in __file__:
            result = get_workspace_paths(
                api_endpoint=API_ENDPOINT,
                api_key=API_KEY,
                workspace_id=args.id,
                limit=args.limit,
                next_token=args.next_token
            )
        elif 'path_components' in __file__:
            result = get_path_components(
                api_endpoint=API_ENDPOINT,
                api_key=API_KEY,
                path_id=args.id,
                limit=args.limit,
                next_token=args.next_token
            )
        else:
            result = get_component_data(
                api_endpoint=API_ENDPOINT,
                api_key=API_KEY,
                component_id=args.id,
                limit=args.limit,
                next_token=args.next_token
            )

        print("Query successful!")
        print(json.dumps(result, indent=2))

        if result.get('nextToken'):
            print(f"\nNext token available: {result['nextToken']}")
            print("Use this token to get the next page")

    except ValueError as e:
        print(f"Configuration error: {str(e)}")
    except Exception as e:
        print(f"Query failed: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
