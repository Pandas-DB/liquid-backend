import os
import boto3
from typing import List, Dict, Optional
from boto3.dynamodb.types import TypeDeserializer

dynamodb = boto3.client('dynamodb')
deserializer = TypeDeserializer()

def query_items(table_name: str, index_name: str, key_name: str, key_value: str) -> List[Dict]:
    """Query items from DynamoDB with pagination."""
    items = []
    last_key = None
    
    while True:
        query_params = {
            'TableName': os.environ[f'{table_name.upper()}_TABLE'],
            'IndexName': index_name,
            'KeyConditionExpression': f'#{key_name} = :value',
            'ExpressionAttributeNames': {
                f'#{key_name}': key_name
            },
            'ExpressionAttributeValues': {
                ':value': {'S': key_value}
            }
        }
        
        if last_key:
            query_params['ExclusiveStartKey'] = last_key
            
        response = dynamodb.query(**query_params)
        items.extend(response.get('Items', []))
        
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break
            
    return [{k: deserializer.deserialize(v) for k, v in item.items()} for item in items]

def batch_delete(table_name: str, items: List[Dict]) -> None:
    """Delete items in batches of 25."""
    # DynamoDB batch_write_item has a limit of 25 items
    batch_size = 25
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        request_items = {
            table_name: [
                {
                    'DeleteRequest': {
                        'Key': {'id': {'S': item['id']}}
                    }
                } for item in batch
            ]
        }
        
        dynamodb.batch_write_item(RequestItems=request_items)
