"""run example:
python3 scripts/admin/cleanup_orphan_workspaces.py admin@test.com --aws-profile test --stage dev --skip-s3
"""

import os
import boto3
import argparse
from typing import Optional, List, Dict, Set
from botocore.exceptions import ClientError
from datetime import datetime


class OrphanWorkspaceCleaner:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev', delete_s3: bool = True):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)
        self.s3 = session.client('s3', region_name=region)
        
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
        
        # S3 bucket name and deletion flag
        self.bucket_name = f"{prefix}-data-bucket"
        self.delete_s3 = delete_s3

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

    def get_all_workspaces(self) -> List[Dict]:
        """Get all workspaces from the workspace table."""
        try:
            response = self.tables['workspace'].scan()
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting workspaces: {str(e)}")
            return []

    def get_workspace_admins(self, workspace_id: str) -> List[Dict]:
        """Get all admin accounts for a workspace."""
        try:
            response = self.tables['account'].scan(
                FilterExpression='workspace_id = :ws_id AND user_is_workspace_admin = :is_admin',
                ExpressionAttributeValues={
                    ':ws_id': workspace_id,
                    ':is_admin': True
                }
            )
            return response.get('Items', [])
        except ClientError as e:
            print(f"Error getting workspace admins: {str(e)}")
            return []

    def delete_workspace_resources(self, workspace_id: str) -> bool:
        """Delete all resources associated with a workspace."""
        try:
            # Get and delete paths
            paths = self.tables['path'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])

            for path in paths:
                print(f"Processing path: {path['id']}")
                
                # Get and delete components
                components = self.tables['component'].scan(
                    FilterExpression='path_id = :path_id',
                    ExpressionAttributeValues={':path_id': path['id']}
                ).get('Items', [])

                for component in components:
                    print(f"Processing component: {component['id']}")
                    
                    # Get and delete data entries
                    data_entries = self.tables['data'].scan(
                        FilterExpression='component_id = :comp_id',
                        ExpressionAttributeValues={':comp_id': component['id']}
                    ).get('Items', [])
                    
                    # Delete S3 objects if configured
                    if self.delete_s3:
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
                    
                    # Delete data entries
                    for data in data_entries:
                        self.tables['data'].delete_item(Key={'id': data['id']})
                        print(f"Deleted data entry: {data['id']}")
                    
                    # Delete component
                    self.tables['component'].delete_item(Key={'id': component['id']})
                    print(f"Deleted component: {component['id']}")
                
                # Delete path
                self.tables['path'].delete_item(Key={'id': path['id']})
                print(f"Deleted path: {path['id']}")
            
            # Delete all accounts associated with the workspace
            accounts = self.tables['account'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])
            
            for account in accounts:
                self.tables['account'].delete_item(Key={'id': account['id']})
                print(f"Deleted account: {account['id']}")
            
            # Finally delete the workspace
            self.tables['workspace'].delete_item(Key={'id': workspace_id})
            print(f"Deleted workspace: {workspace_id}")
            
            return True
            
        except Exception as e:
            print(f"Error deleting workspace resources: {str(e)}")
            return False

    def cleanup_orphaned_components(self) -> None:
        """Clean up components and data that don't have valid parent resources."""
        try:
            print("\nChecking for orphaned components and data...")

            # Get all workspaces for validation
            workspaces = {ws['id']: ws for ws in self.tables['workspace'].scan().get('Items', [])}
            paths = {path['id']: path for path in self.tables['path'].scan().get('Items', [])}

            # Check all components
            components = self.tables['component'].scan().get('Items', [])
            orphaned_components = []

            for component in components:
                is_orphaned = False

                # Check if workspace exists
                if component['workspace_id'] not in workspaces:
                    print(f"Component {component['id']} references non-existent workspace {component['workspace_id']}")
                    is_orphaned = True

                # Check if path exists
                if component['path_id'] not in paths:
                    print(f"Component {component['id']} references non-existent path {component['path_id']}")
                    is_orphaned = True

                # Check if path belongs to correct workspace
                if not is_orphaned and paths[component['path_id']]['workspace_id'] != component['workspace_id']:
                    print(f"Component {component['id']} has mismatched workspace_id with its path")
                    is_orphaned = True

                if is_orphaned:
                    orphaned_components.append(component)

            # Clean up orphaned components and their data
            for component in orphaned_components:
                # Delete associated data first
                data_entries = self.tables['data'].query(
                    IndexName='ComponentDataIndex',
                    KeyConditionExpression='component_id = :comp_id',
                    ExpressionAttributeValues={':comp_id': component['id']}
                ).get('Items', [])

                for data in data_entries:
                    # Delete from S3 if applicable
                    if 's3_location' in data:
                        try:
                            self.s3.delete_object(
                                Bucket=self.bucket_name,
                                Key=data['s3_location']
                            )
                            print(f"Deleted orphaned S3 object: {data['s3_location']}")
                        except Exception as e:
                            print(f"Warning: Failed to delete S3 object: {str(e)}")

                    # Delete data entry
                    self.tables['data'].delete_item(Key={'id': data['id']})
                    print(f"Deleted orphaned data entry: {data['id']}")

                # Delete the component
                self.tables['component'].delete_item(Key={'id': component['id']})
                print(f"Deleted orphaned component: {component['id']}")

            print(
                f"\nCleanup complete. Removed {len(orphaned_components)} orphaned components and their associated data.")

        except Exception as e:
            print(f"Error during orphaned component cleanup: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Find and cleanup orphaned workspaces')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--skip-s3', action='store_true', help='Skip deletion of S3 objects')
    parser.add_argument('--execute', action='store_true', help='Actually perform deletions (default is dry run)')
    
    args = parser.parse_args()
    
    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"S3 deletion: {'disabled' if args.skip_s3 else 'enabled'}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")
    
    if args.execute:
        confirm = input("Are you sure you want to delete orphaned workspaces? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            exit(0)
    
    cleaner = OrphanWorkspaceCleaner(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage,
        delete_s3=not args.skip_s3
    )
    
    if not cleaner.check_tables_exist():
        print("Required tables do not exist. Please check your configuration.")
        exit(1)
    
    cleaner.cleanup_orphaned_workspaces(dry_run=not args.execute)
