"""run example:
python3 scripts/admin/create_user.py admin@test.com --aws-profile test --stage dev --create-workspace
"""

import os
import boto3
import argparse
from datetime import datetime
from typing import Optional, Dict, Any


def create_admin_user(
        email: str,
        user_table_name: str,
        account_table_name: str,
        workspace_table_name: str,
        region: str = 'eu-west-1',
        profile: Optional[str] = None,
        create_workspace: bool = False  # Only this flag is needed now
) -> Dict[str, Any]:
    """
    Create an admin user with optional workspace and account.

    Args:
        email: Email address for the admin user
        user_table_name: Name of the User DynamoDB table
        account_table_name: Name of the Account DynamoDB table
        workspace_table_name: Name of the Workspace DynamoDB table
        region: AWS region
        profile: AWS profile name (optional)
        create_workspace: Whether to create a workspace and associated account (default: False)

    Returns:
        Dict containing the created IDs (user_id and optionally workspace_id and account_id)
    """
    # Setup AWS session
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()

    dynamodb = session.resource('dynamodb', region_name=region)

    # Get table references
    user_table = dynamodb.Table(user_table_name)

    # Create timestamps
    current_time = datetime.now().isoformat()

    result = {}

    # Create user
    user_id = f"user-{str(uuid.uuid4())}"
    try:
        user_table.put_item(Item={
            'id': user_id,
            'email': email,
            'created_at': current_time,
            'updated_at': current_time,
            'metadata': '{"role": "admin"}'
        })
        print(f"Created user with ID: {user_id}")
        result['user_id'] = user_id
    except ClientError as e:
        print(f"Error creating user: {str(e)}")
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

            # Always create account when workspace is created
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

    args = parser.parse_args()

    # Construct table names based on stage
    prefix = f"workspace-management-{args.stage}"
    user_table = f"{prefix}-user"
    account_table = f"{prefix}-account"
    workspace_table = f"{prefix}-workspace"

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"Creating user: {args.email}")
    print(f"Create workspace and account: {args.create_workspace}\n")

    result = create_admin_user(
        email=args.email,
        user_table_name=user_table,
        account_table_name=account_table,
        workspace_table_name=workspace_table,
        region=args.region,
        profile=args.aws_profile,
        create_workspace=args.create_workspace
    )

    print("\nCreation completed successfully!")
    for key, value in result.items():
        print(f"{key}: {value}")
