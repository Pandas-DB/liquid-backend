"""run example:
python3 scripts/admin/delete_user_accounts.py admin@test.com ws-uuid-1 ws-uuid-2 ws-uuid-3 --aws-profile test --stage dev --execute --skip-s3
"""


import os
import boto3
import argparse
from typing import Optional, List, Dict
from botocore.exceptions import ClientError


class UserAccountDeleter:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev',
                 delete_s3: bool = True):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)
        self.s3 = session.client('s3', region_name=region)

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

        self.bucket_name = f"{prefix}-data-bucket"
        self.delete_s3 = delete_s3

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

    def get_specific_accounts(self, user_id: str, workspace_ids: List[str]) -> List[Dict]:
        """Get specific accounts for user-workspace combinations."""
        accounts = []
        try:
            for ws_id in workspace_ids:
                response = self.tables['account'].scan(
                    FilterExpression='user_id = :uid AND workspace_id = :wsid',
                    ExpressionAttributeValues={
                        ':uid': user_id,
                        ':wsid': ws_id
                    }
                )
                if response['Items']:
                    accounts.append(response['Items'][0])
        except ClientError as e:
            print(f"Error getting accounts: {str(e)}")
        return accounts

    def delete_workspace_cascade(self, workspace_id: str) -> bool:
        """Delete workspace and all its resources."""
        try:
            print(f"\nStarting cascade deletion for workspace: {workspace_id}")

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

                    if self.delete_s3:
                        for data in data_entries:
                            if 's3_location' in data:
                                self.s3.delete_object(
                                    Bucket=self.bucket_name,
                                    Key=data['s3_location']
                                )
                                print(f"Deleted S3 object: {data['s3_location']}")

                    for data in data_entries:
                        self.tables['data'].delete_item(Key={'id': data['id']})
                        print(f"Deleted data entry: {data['id']}")

                    self.tables['component'].delete_item(Key={'id': component['id']})
                    print(f"Deleted component: {component['id']}")

                self.tables['path'].delete_item(Key={'id': path['id']})
                print(f"Deleted path: {path['id']}")

            # Delete all accounts for this workspace
            accounts = self.tables['account'].scan(
                FilterExpression='workspace_id = :ws_id',
                ExpressionAttributeValues={':ws_id': workspace_id}
            ).get('Items', [])

            for account in accounts:
                self.tables['account'].delete_item(Key={'id': account['id']})
                print(f"Deleted account: {account['id']}")

            self.tables['workspace'].delete_item(Key={'id': workspace_id})
            print(f"Deleted workspace: {workspace_id}")

            return True
        except Exception as e:
            print(f"Error in cascade deletion: {str(e)}")
            return False

    def delete_specific_accounts(self, email: str, workspace_ids: List[str], dry_run: bool = True) -> bool:
        """Delete specific accounts for a user."""
        try:
            # Verify user exists
            user = self.get_user_by_email(email)
            if not user:
                print(f"User with email {email} not found!")
                return False

            print(f"\nFound user: {user['id']} ({user['email']})")

            # Get specified accounts
            accounts = self.get_specific_accounts(user['id'], workspace_ids)
            if not accounts:
                print("No matching accounts found!")
                return True

            print(f"\nFound {len(accounts)} matching accounts:")
            admin_workspaces = []
            regular_accounts = []

            for account in accounts:
                ws_id = account['workspace_id']
                is_admin = account['user_is_workspace_admin']
                print(f"Workspace: {ws_id}")
                print(f"Admin access: {is_admin}")
                if is_admin:
                    admin_workspaces.append(account)
                else:
                    regular_accounts.append(account)

            if dry_run:
                if admin_workspaces:
                    print("\nAdmin workspaces that would be cascade deleted:")
                    for acc in admin_workspaces:
                        print(f"- {acc['workspace_id']}")
                if regular_accounts:
                    print("\nRegular accounts that would be removed:")
                    for acc in regular_accounts:
                        print(f"- Account {acc['id']} for workspace {acc['workspace_id']}")
                print("\nDRY RUN - No deletions performed")
                return True

            # Perform deletions
            for account in admin_workspaces:
                print(f"\nProcessing admin account for workspace {account['workspace_id']}")
                if self.delete_workspace_cascade(account['workspace_id']):
                    print(f"Successfully deleted workspace {account['workspace_id']} and all resources")
                else:
                    print(f"Failed to delete workspace {account['workspace_id']}")

            for account in regular_accounts:
                self.tables['account'].delete_item(Key={'id': account['id']})
                print(f"Deleted regular account {account['id']} for workspace {account['workspace_id']}")

            return True

        except Exception as e:
            print(f"Error deleting accounts: {str(e)}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete specific user accounts')
    parser.add_argument('email', help='Email of the user')
    parser.add_argument('workspace_ids', nargs='+', help='List of workspace IDs to remove access from')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--skip-s3', action='store_true', help='Skip deletion of S3 objects')
    parser.add_argument('--execute', action='store_true', help='Actually perform deletions (default is dry run)')

    args = parser.parse_args()

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"User: {args.email}")
    print(f"Workspace IDs: {args.workspace_ids}")
    print(f"S3 deletion: {'disabled' if args.skip_s3 else 'enabled'}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    if args.execute:
        confirm = input(
            "Are you sure you want to delete these specific accounts? Admin accounts will trigger cascade deletion! (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            exit(0)

    deleter = UserAccountDeleter(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage,
        delete_s3=not args.skip_s3
    )

    success = deleter.delete_specific_accounts(
        args.email,
        args.workspace_ids,
        dry_run=not args.execute
    )

    if not success:
        exit(1)
