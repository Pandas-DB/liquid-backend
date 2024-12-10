import os
import json
import boto3
import logging
from typing import Dict, Any, Tuple, Optional
from boto3.dynamodb.types import TypeDeserializer
from .utils import get_entity_info, format_s3_key
from ...lib.common_utils import setup_logging

logger = setup_logging(__name__)
dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
deserializer = TypeDeserializer()

def handler(event: Dict[str, Any], context: Any) -> None:
    """Handle DynamoDB Stream events for data entries."""
    bucket_name = os.environ['DATA_BUCKET']
    
    for record in event['Records']:
        try:
            # Process record based on event type
            if record['eventName'] == 'INSERT':
                handle_insert(record, bucket_name)
            elif record['eventName'] == 'REMOVE':
                handle_remove(record, bucket_name)
                
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            # Don't raise the error to prevent Lambda retry
            continue

def handle_insert(record: Dict[str, Any], bucket_name: str) -> None:
    """Handle INSERT events by writing to S3."""
    new_image = {k: deserializer.deserialize(v) for k, v in record['dynamodb']['NewImage'].items()}
    
    # Check if we should add to data lake
    if not new_image.get('addToDataLake', True):
        logger.info(f"Skipping S3 write for data {new_image['id']} (addToDataLake=False)")
        return

    try:
        # Get path components for S3 key
        workspace_name, path_name, component_name = get_entity_info(new_image['component_id'])
        
        # Format S3 key
        s3_key = format_s3_key(workspace_name, path_name, component_name, new_image['id'])
        
        # Write to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(json.loads(new_image['data'])),
            ContentType='application/json'
        )
        
        # Update DynamoDB with S3 location
        s3_location = f"s3://{bucket_name}/{s3_key}"
        dynamodb.update_item(
            TableName=os.environ['DATA_TABLE'],
            Key={'id': {'S': new_image['id']}},
            UpdateExpression='SET s3_location = :loc',
            ExpressionAttributeValues={
                ':loc': {'S': s3_location}
            }
        )
        
        logger.info(f"Successfully wrote data {new_image['id']} to S3: {s3_location}")
        
    except Exception as e:
        logger.error(f"Error writing to S3: {str(e)}", exc_info=True)
        raise

def handle_remove(record: Dict[str, Any], bucket_name: str) -> None:
    """Handle REMOVE events by deleting from S3 if needed."""
    old_image = {k: deserializer.deserialize(v) for k, v in record['dynamodb']['OldImage'].items()}
    
    # Check if we should delete from data lake
    if not old_image.get('deleteInDataLake', True):
        logger.info(f"Skipping S3 delete for data {old_image['id']} (deleteInDataLake=False)")
        return

    # Check if s3_location exists
    s3_location = old_image.get('s3_location')
    if not s3_location:
        logger.info(f"No S3 location found for data {old_image['id']}")
        return

    try:
        # Parse bucket and key from s3_location
        _, bucket_name, *key_parts = s3_location.split('/')
        key = '/'.join(key_parts)
        
        # Delete from S3
        s3.delete_object(
            Bucket=bucket_name,
            Key=key
        )
        
        logger.info(f"Successfully deleted data {old_image['id']} from S3")
        
    except Exception as e:
        logger.error(f"Error deleting from S3: {str(e)}", exc_info=True)
        # Don't raise error as per requirements
