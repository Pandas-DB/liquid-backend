"""run example:
python3 scripts/admin/create_user.py admin@test.com --aws-profile test --stage dev --create-workspace
"""

import os
import boto3
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from botocore.exceptions import ClientError


def get_user_pool_id(cognito_client, pool_name: str) -> Optional[str]:
    """
    Get the User Pool ID for a given pool name.
    """
    try:
        response = cognito_client.list_user_pools(MaxResults=60)
        for pool in response['UserPools']:
            if pool['Name'] == pool_name:
                return pool['Id']

        while 'NextToken' in response:
            response = cognito_client.list_user_pools(NextToken=response['NextToken'], MaxResults=60)
            for pool in response['UserPools']:
                if pool['Name'] == pool_name:
                    return pool['Id']

        return None
    except ClientError as e:
        print(f"Error getting user pool ID: {str(e)}")
        raise


def create_admin_user(
        email: str,
        user_table_name: str,
        account_table_name: str,
        workspace_table_name: str,
        user_pool_id: str,
        region: str = 'eu-west-1',
        profile: Optional[str] = None,
        create_workspace: bool = False
) -> Dict[str, Any]:
    """
    Create an admin user in both DynamoDB and Cognito with optional workspace and account.
    """
    # Setup AWS session
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()

    dynamodb = session.resource('dynamodb', region_name=region)
    cognito = session.client('cognito-idp', region_name=region)

    # Get table references
    user_table = dynamodb.Table(user_table_name)

    # Create timestamps
    current_time = datetime.now().isoformat()

    result = {}

    # Create user ID to be used in both systems
    user_id = f"user-{str(uuid.uuid4())}"
    temp_password = f"Welcome1!{str(uuid.uuid4())[:8]}"  # Temporary password meeting Cognito requirements

    try:
        # Create Cognito user first
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:user_id', 'Value': user_id}
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Suppress email sending - we'll handle communication separately
        )

        # Set password as permanent to avoid forced change
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=temp_password,
            Permanent=True
        )

        print(f"Created Cognito user: {email}")
        result['temporary_password'] = temp_password

        # Create DynamoDB user
        user_table.put_item(Item={
            'id': user_id,
            'email': email,
            'created_at': current_time,
            'updated_at': current_time,
            'metadata': '{"role": "admin"}',
            'cognito_username': email  # Store Cognito username for reference
        })
        print(f"Created DynamoDB user with ID: {user_id}")
        result['user_id'] = user_id

    except ClientError as e:
        print(f"Error creating user: {str(e)}")
        # Clean up if partial creation occurred
        try:
            cognito.admin_delete_user(
                UserPoolId=user_pool_id,
                Username=email
            )
        except:
            pass
        raise

    if create_workspace:
        # Create workspace
        workspace_table = dynamodb.Table(workspace_table_name)
        workspace_id = f"ws-{str(uuid.uuid4())}"
        workspace_name = f"Admin Workspace - {email}"
        try:
            workspace_table.put_item(Item={
                'id': workspace_id,
                'name': workspace_name,
                'created_at': current_time,
                'updated_at': current_time,
                'metadata': '{"type": "admin"}'
            })
            print(f"Created workspace with ID: {workspace_id}")
            result['workspace_id'] = workspace_id

            # Create account
            account_table = dynamodb.Table(account_table_name)
            account_id = f"acc-{str(uuid.uuid4())}"
            account_table.put_item(Item={
                'id': account_id,
                'user_id': user_id,
                'workspace_id': workspace_id,
                'user_is_workspace_admin': True,
                'created_at': current_time,
                'updated_at': current_time
            })
            print(f"Created account with ID: {account_id}")
            result['account_id'] = account_id

        except ClientError as e:
            print(f"Error creating workspace and account: {str(e)}")
            raise

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create an admin user with optional workspace')
    parser.add_argument('email', help='Email address for the admin user')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--create-workspace', action='store_true',
                        help='Create workspace for user (will also create an account)')
    parser.add_argument('--user-pool-id', help='Cognito User Pool ID (if not provided, will try to find by name)')

    args = parser.parse_args()

    # Setup AWS session for initial operations
    session = boto3.Session(profile_name=args.aws_profile)
    cognito = session.client('cognito-idp', region_name=args.region)

    # Construct table names and user pool name based on stage
    prefix = f"liquid-backend-{args.stage}"
    user_table = f"{prefix}-user"
    account_table = f"{prefix}-account"
    workspace_table = f"{prefix}-workspace"

    # Get user pool ID either from argument or by looking up the name
    user_pool_id = args.user_pool_id
    if not user_pool_id:
        user_pool_name = f"{prefix}-user-pool"
        user_pool_id = get_user_pool_id(cognito, user_pool_name)
        if not user_pool_id:
            raise ValueError(f"Could not find user pool with name: {user_pool_name}")

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"User Pool ID: {user_pool_id}")
    print(f"Creating user: {args.email}")
    print(f"Create workspace and account: {args.create_workspace}\n")

    result = create_admin_user(
        email=args.email,
        user_table_name=user_table,
        account_table_name=account_table,
        workspace_table_name=workspace_table,
        user_pool_id=user_pool_id,
        region=args.region,
        profile=args.aws_profile,
        create_workspace=args.create_workspace
    )

    print("\nCreation completed successfully!")
    for key, value in result.items():
        print(f"{key}: {value}")
