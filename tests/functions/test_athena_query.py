from os import getenv
import requests
import json


def execute_athena_query(api_endpoint: str, api_key: str, query: str):
    """
    Send Athena query execution request to API Gateway endpoint

    Args:
        api_endpoint: Your API Gateway endpoint for the Athena query Lambda
        api_key: Your API key
        query: SQL query to execute in Athena
    """

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key
    }

    # Request payload
    payload = {
        'query': query
    }

    # Make the request
    try:
        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes

        result = response.json()

        # Check for errors in the response
        if result.get('statusCode') != 200:
            raise Exception(f"Query failed: {result.get('body')}")

        return result['body']

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        raise
    except Exception as e:
        print(f"Error: {str(e)}")
        raise


# Example usage
if __name__ == "__main__":
    # Your API Gateway configuration
    API_ENDPOINT = getenv('ATHENA_API_ENDPOINT')
    API_KEY = getenv('API_KEY')

    # Example Athena query
    test_query = """
    SELECT 
        workspace_id,
        COUNT(*) as record_count,
        MIN(data) as first_record,
        MAX(data) as last_record
    FROM data_table
    GROUP BY workspace_id
    LIMIT 10
    """

    try:
        if not API_ENDPOINT or not API_KEY:
            raise ValueError("ATHENA_API_ENDPOINT and API_KEY environment variables must be set")

        print(f"Making request to: {API_ENDPOINT}")
        print(f"Executing query:\n{test_query}")

        result = execute_athena_query(
            api_endpoint=API_ENDPOINT,
            api_key=API_KEY,
            query=test_query
        )

        print("\nQuery execution successful!")
        print(json.dumps(result, indent=2))

    except ValueError as e:
        print(f"Configuration error: {str(e)}")
    except Exception as e:
        print(f"Failed to execute query: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
