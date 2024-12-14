# src/functions/athena_handlers/execute_query.py

import os
import boto3
import time
from src.lib.common_utils import handle_error

athena = boto3.client('athena')

def wait_for_query(query_execution_id):
    """Wait for an Athena query to complete."""
    while True:
        response = athena.get_query_execution(QueryExecutionId=query_execution_id)
        state = response['QueryExecution']['Status']['State']
        
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            return state
        
        time.sleep(1)  # Wait before checking again

def execute_query(query_string):
    """Execute an Athena query and return results."""
    try:
        # Start query execution
        response = athena.start_query_execution(
            QueryString=query_string,
            QueryExecutionContext={
                'Database': os.environ['ATHENA_DATABASE']
            },
            WorkGroup=os.environ['ATHENA_WORKGROUP']
        )
        
        query_execution_id = response['QueryExecutionId']
        
        # Wait for query to complete
        final_state = wait_for_query(query_execution_id)
        
        if final_state == 'SUCCEEDED':
            # Get results
            results = athena.get_query_results(
                QueryExecutionId=query_execution_id
            )
            return results
            
        else:
            raise Exception(f"Query failed with state: {final_state}")
            
    except Exception as e:
        raise handle_error(e)

def handler(event, context):
    """Lambda handler for Athena query execution."""
    try:
        if 'query' not in event:
            return {
                'statusCode': 400,
                'body': 'Query parameter is required'
            }

        query = event['query']
        results = execute_query(query)
        
        return {
            'statusCode': 200,
            'body': results
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
