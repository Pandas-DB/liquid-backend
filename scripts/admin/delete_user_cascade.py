"""run example:
python3 scripts/admin/delete_user_cascade.py admin@test.com --aws-profile test --stage dev --skip-s3
"""

import os
import boto3
import argparse
from typing import Optional, List, Set, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime


class ResourceDeleter:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev',
                 delete_s3: bool = True):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)
        self.s3 = session.client('s3', region_name=region)
        self.cognito = session.client('cognito-idp', region_name=region)
        self.delete_s3 = delete_s3
        self.stage = stage

        # Initialize table names
        prefix = f"liquid-backend-{stage}"
        self.table_names = {
            'user': f"{prefix}-user",
            'account': f"{prefix}-account",
            'workspace': f"{prefix}-workspace",
            'path': f"{prefix}-path",
            'component': f"{prefix}-component",
            'data': f"{prefix}-data"
        }

        # Initialize table references
        self.tables = {
            name: self.dynamodb.Table(table_name)
            for name, table_name in self.table_names.items()
        }

        # S3 bucket name
        self.bucket_name = f"{prefix}-data-bucket"

        # Get user pool ID
        self.user_pool_id = self.get_user_pool_id(f"{prefix}-user-pool")

    def delete_s3_objects(self, data_entries: List[Dict]):
        """Delete associated S3 objects."""
        if not self.delete_s3:
            print("Skipping S3 deletion as per configuration")
            return

        for data in data_entries:
            if 's3_location' in data:
                try:
                    self.s3.delete_object(
                        Bucket=self.bucket_name,
                        Key=data['s3_location']
                    )
                    print(f"Deleted S3 object: {data['s3_location']}")
                except ClientError as e:
                    print(f"Error deleting S3 object: {str(e)}")

    def get_user_pool_id(self, pool_name: str) -> Optional[str]:
        """Get the User Pool ID for a given pool name."""
        try:
            response = self.cognito.list_user_pools(MaxResults=60)
            for pool in response['UserPools']:
                if pool['Name'] == pool_name:
                    return pool['Id']

            while 'NextToken' in response:
                response = self.cognito.list_user_pools(
                    NextToken=response['NextToken'],
                    MaxResults=60
                )
                for pool in response['UserPools']:
                    if pool['Name'] == pool_name:
                        return pool['Id']

            print(f"Warning: Could not find user pool with name: {pool_name}")
            return None
        except Exception as e:
            print(f"Error getting user pool ID: {str(e)}")
            return None

    def delete_cognito_user(self, email: str) -> bool:
        """Delete user from Cognito User Pool."""
        if not self.user_pool_id:
            print("Warning: No user pool ID found, skipping Cognito user deletion")
            return False

        try:
            self.cognito.admin_delete_user(
                UserPoolId=self.user_pool_id,
                Username=email
            )
            print(f"Deleted Cognito user: {email}")
            return True
        except self.cognito.exceptions.UserNotFoundException:
            print(f"Cognito user not found: {email}")
            return True  # Return True as this is not an error case
        except Exception as e:
            print(f"Error deleting Cognito user: {str(e)}")
            return False

    def check_tables_exist(self) -> bool:
        """Verify all required tables exist."""
        try:
            existing_tables = [t.name for t in self.dynamodb.tables.all()]
            for table_name in self.table_names.values():
                if table_name not in existing_tables:
                    print(f"Table {table_name} does not exist!")
                    return False
            return True
        except Exception as e:
            print(f"Error checking tables: {str(e)}")
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Find user by email."""
        try:
            response = self.tables['user'].scan(
                FilterExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            items = response.get('Items', [])
            return items[0] if items else None
        except ClientError as e:
            print(f"Error finding user: {str(e)}")
            return None

    def delete_cascade(self, email: str) -> bool:
        """Delete user and all associated resources including Cognito user."""
        try:
            # Find user
            user = self.get_user_by_email(email)
            if not user:
                print(f"User with email {email} not found")
                return False

            print(f"\nFound user: {user['id']} ({user['email']})")

            # Delete Cognito user first
            if not self.delete_cognito_user(email):
                print("Failed to delete Cognito user, stopping cascade deletion")
                return False

            # Get user's accounts
            accounts = self.tables['account'].query(
                IndexName='UserWorkspaceIndex',
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user['id']}
            ).get('Items', [])

            print(f"Found {len(accounts)} accounts")

            # Get workspaces where user is admin
            admin_workspaces = {
                acc['workspace_id'] for acc in accounts
                if acc.get('user_is_workspace_admin', False)
            }
            print(f"User is admin of {len(admin_workspaces)} workspaces")

            # For each admin workspace, delete all resources
            for workspace_id in admin_workspaces:
                print(f"\nProcessing workspace: {workspace_id}")

                # Get all data entries directly using WorkspaceDataIndex
                data_entries = self.tables['data'].query(
                    IndexName='WorkspaceDataIndex',
                    KeyConditionExpression='workspace_id = :ws_id',
                    ExpressionAttributeValues={':ws_id': workspace_id}
                ).get('Items', [])

                # Delete S3 objects if enabled
                self.delete_s3_objects(data_entries)

                # Delete all data entries
                for data in data_entries:
                    self.tables['data'].delete_item(Key={'id': data['id']})
                    print(f"Deleted data entry: {data['id']}")

                # Delete components
                components = self.tables['component'].query(
                    IndexName='WorkspaceComponentIndex',
                    KeyConditionExpression='workspace_id = :ws_id',
                    ExpressionAttributeValues={':ws_id': workspace_id}
                ).get('Items', [])

                for component in components:
                    self.tables['component'].delete_item(Key={'id': component['id']})
                    print(f"Deleted component: {component['id']}")

                # Delete paths
                paths = self.tables['path'].query(
                    IndexName='WorkspacePathIndex',
                    KeyConditionExpression='workspace_id = :ws_id',
                    ExpressionAttributeValues={':ws_id': workspace_id}
                ).get('Items', [])

                for path in paths:
                    self.tables['path'].delete_item(Key={'id': path['id']})
                    print(f"Deleted path: {path['id']}")

                # Delete the workspace
                self.tables['workspace'].delete_item(Key={'id': workspace_id})
                print(f"Deleted workspace: {workspace_id}")

            # Delete all user accounts
            for account in accounts:
                self.tables['account'].delete_item(Key={'id': account['id']})
                print(f"Deleted account: {account['id']}")

            # Finally, delete the user
            self.tables['user'].delete_item(Key={'id': user['id']})
            print(f"\nDeleted user: {user['id']}")

            return True

        except Exception as e:
            print(f"Error during cascade deletion: {str(e)}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete a user and all associated resources')
    parser.add_argument('email', help='Email address of the user to delete')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--skip-s3', action='store_true', help='Skip deletion of S3 objects')

    args = parser.parse_args()

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"Deleting user: {args.email}")
    print(f"S3 deletion: {'disabled' if args.skip_s3 else 'enabled'}\n")

    # Confirmation
    confirm = input("This will delete the user and ALL associated resources. Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        exit(0)

    deleter = ResourceDeleter(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage,
        delete_s3=not args.skip_s3
    )

    if not deleter.check_tables_exist():
        print("Required tables do not exist. Please check your configuration.")
        exit(1)

    if deleter.delete_cascade(args.email):
        print("\nUser and associated resources deleted successfully!")
    else:
        print("\nFailed to complete deletion process")
        exit(1)
