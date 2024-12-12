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
        self.delete_s3 = delete_s3
        
        # Initialize table names
        prefix = f"workspace-management-{stage}"
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
    
    def get_user_accounts(self, user_id: str) -> List[Dict]:
        """Get all accounts for a user."""
        try:
            response = self.tables['account'].scan(
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting user accounts: {str(e)}")
            return []
    
    def get_admin_workspaces(self, accounts: List[Dict]) -> Set[str]:
        """Get workspace IDs where user is admin."""
        return {
            acc['workspace_id'] for acc in accounts 
            if acc.get('user_is_workspace_admin', False)
        }
    
    def get_workspace_paths(self, workspace_id: str) -> List[Dict]:
        """Get all paths in a workspace."""
        try:
            response = self.tables['path'].scan(
                FilterExpression='workspace_id = :workspace_id',
                ExpressionAttributeValues={':workspace_id': workspace_id}
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting workspace paths: {str(e)}")
            return []
    
    def get_path_components(self, path_id: str) -> List[Dict]:
        """Get all components in a path."""
        try:
            response = self.tables['component'].scan(
                FilterExpression='path_id = :path_id',
                ExpressionAttributeValues={':path_id': path_id}
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting path components: {str(e)}")
            return []
    
    def get_component_data(self, component_id: str) -> List[Dict]:
        """Get all data entries for a component."""
        try:
            response = self.tables['data'].scan(
                FilterExpression='component_id = :component_id',
                ExpressionAttributeValues={':component_id': component_id}
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting component data: {str(e)}")
            return []

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

    def delete_cascade(self, email: str) -> bool:
        """Delete user and all associated resources."""
        try:
            # Find user
            user = self.get_user_by_email(email)
            if not user:
                print(f"User with email {email} not found")
                return False
            
            print(f"\nFound user: {user['id']} ({user['email']})")
            
            # Get user's accounts
            accounts = self.get_user_accounts(user['id'])
            print(f"Found {len(accounts)} accounts")
            
            # Get workspaces where user is admin
            admin_workspaces = self.get_admin_workspaces(accounts)
            print(f"User is admin of {len(admin_workspaces)} workspaces")
            
            # For each admin workspace, delete all resources
            for workspace_id in admin_workspaces:
                print(f"\nProcessing workspace: {workspace_id}")
                
                # Get and delete paths
                paths = self.get_workspace_paths(workspace_id)
                for path in paths:
                    print(f"Processing path: {path['id']}")
                    
                    # Get and delete components
                    components = self.get_path_components(path['id'])
                    for component in components:
                        print(f"Processing component: {component['id']}")
                        
                        # Get and delete data entries
                        data_entries = self.get_component_data(component['id'])
                        
                        # Delete S3 objects first
                        self.delete_s3_objects(data_entries)
                        
                        # Delete data entries
                        for data in data_entries:
                            self.tables['data'].delete_item(
                                Key={'id': data['id']}
                            )
                            print(f"Deleted data entry: {data['id']}")
                        
                        # Delete component
                        self.tables['component'].delete_item(
                            Key={'id': component['id']}
                        )
                        print(f"Deleted component: {component['id']}")
                    
                    # Delete path
                    self.tables['path'].delete_item(
                        Key={'id': path['id']}
                    )
                    print(f"Deleted path: {path['id']}")
                
                # Delete workspace
                self.tables['workspace'].delete_item(
                    Key={'id': workspace_id}
                )
                print(f"Deleted workspace: {workspace_id}")
            
            # Delete all user accounts
            for account in accounts:
                self.tables['account'].delete_item(
                    Key={'id': account['id']}
                )
                print(f"Deleted account: {account['id']}")
            
            # Finally, delete the user
            self.tables['user'].delete_item(
                Key={'id': user['id']}
            )
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
