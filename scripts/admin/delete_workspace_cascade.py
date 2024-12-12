"""run example:
python3 scripts/admin/delete_workspace_cascade.py ws-20241212083321 --aws-profile test --stage dev --execute
"""

import os
import boto3
import argparse
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError
from datetime import datetime


class WorkspaceDeleter:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev',
                 delete_s3: bool = True):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)
        self.s3 = session.client('s3', region_name=region)

        # Initialize table names
        prefix = f"liquid-backend-{stage}"
        self.table_names = {
            'workspace': f"{prefix}-workspace",
            'account': f"{prefix}-account",
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

    def get_workspace(self, workspace_id: str) -> Optional[Dict]:
        """Get workspace details."""
        try:
            response = self.tables['workspace'].get_item(Key={'id': workspace_id})
            return response.get('Item')
        except ClientError as e:
            print(f"Error getting workspace: {str(e)}")
            return None

    def summarize_workspace_resources(self, workspace_id: str) -> Dict[str, int]:
        """Get a count of all resources associated with the workspace."""
        try:
            # Count accounts
            accounts = self.tables['account'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])

            # Count paths
            paths = self.tables['path'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])

            # Count components and data
            component_count = 0
            data_count = 0
            s3_objects_count = 0

            for path in paths:
                components = self.tables['component'].scan(
                    FilterExpression='path_id = :path_id',
                    ExpressionAttributeValues={':path_id': path['id']}
                ).get('Items', [])
                component_count += len(components)

                for component in components:
                    data_entries = self.tables['data'].scan(
                        FilterExpression='component_id = :comp_id',
                        ExpressionAttributeValues={':comp_id': component['id']}
                    ).get('Items', [])
                    data_count += len(data_entries)
                    s3_objects_count += len([d for d in data_entries if 's3_location' in d])

            return {
                'accounts': len(accounts),
                'paths': len(paths),
                'components': component_count,
                'data_entries': data_count,
                's3_objects': s3_objects_count
            }
        except ClientError as e:
            print(f"Error getting resource summary: {str(e)}")
            return {}

    def delete_workspace_cascade(self, workspace_id: str, dry_run: bool = True) -> bool:
        """Delete workspace and all its resources."""
        try:
            # First verify workspace exists
            workspace = self.get_workspace(workspace_id)
            if not workspace:
                print(f"Workspace {workspace_id} not found")
                return False

            print(f"\nWorkspace details:")
            print(f"ID: {workspace['id']}")
            print(f"Name: {workspace['name']}")
            print(f"Created at: {workspace['created_at']}")

            # Get resource summary
            summary = self.summarize_workspace_resources(workspace_id)
            print("\nResources to be deleted:")
            print(f"Accounts: {summary['accounts']}")
            print(f"Paths: {summary['paths']}")
            print(f"Components: {summary['components']}")
            print(f"Data entries: {summary['data_entries']}")
            print(f"S3 objects: {summary['s3_objects']}")

            if dry_run:
                print("\nDRY RUN - No deletions performed")
                return True

            # Get and delete paths
            paths = self.tables['path'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])

            for path in paths:
                print(f"\nProcessing path: {path['id']}")

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
            print(f"\nDeleted workspace: {workspace_id}")

            return True

        except Exception as e:
            print(f"Error during cascade deletion: {str(e)}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete a workspace and all its resources')
    parser.add_argument('workspace_id', help='ID of the workspace to delete')
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
        confirm = input("Are you sure you want to delete this workspace and ALL its resources? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            exit(0)

    deleter = WorkspaceDeleter(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage,
        delete_s3=not args.skip_s3
    )

    if not deleter.check_tables_exist():
        print("Required tables do not exist. Please check your configuration.")
        exit(1)

    success = deleter.delete_workspace_cascade(args.workspace_id, dry_run=not args.execute)
    if not success:
        exit(1)
