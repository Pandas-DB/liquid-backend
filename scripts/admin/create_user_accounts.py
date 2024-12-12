"""run example:
python3 scripts/admin/create_user_accounts.py admin@test.com ws-uuid-1 ws-uuid-2 ws-uuid-3 --aws-profile test --stage dev --as-admin --execute
"""
import os
import boto3
import argparse
from typing import Optional, List, Dict
from datetime import datetime
from botocore.exceptions import ClientError
from ...lib.common_utils import generate_id


class UserAccountCreator:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev'):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)

        # Initialize table names
        prefix = f"workspace-management-{stage}"
        self.table_names = {
            'user': f"{prefix}-user",
            'account': f"{prefix}-account",
            'workspace': f"{prefix}-workspace",
        }

        # Initialize table references
        self.tables = {
            name: self.dynamodb.Table(table_name)
            for name, table_name in self.table_names.items()
        }

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

    def verify_workspaces_exist(self, workspace_ids: List[str]) -> bool:
        """Verify all workspace IDs exist."""
        for ws_id in workspace_ids:
            try:
                response = self.tables['workspace'].get_item(Key={'id': ws_id})
                if 'Item' not in response:
                    print(f"Workspace {ws_id} does not exist!")
                    return False
            except ClientError as e:
                print(f"Error verifying workspace {ws_id}: {str(e)}")
                return False
        return True

    def get_existing_accounts(self, user_id: str, workspace_ids: List[str]) -> List[Dict]:
        """Get any existing accounts for user-workspace combinations."""
        existing_accounts = []
        try:
            # Get all accounts for user
            response = self.tables['account'].scan(
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )

            # Filter for relevant workspace_ids
            for account in response.get('Items', []):
                if account['workspace_id'] in workspace_ids:
                    existing_accounts.append(account)

            return existing_accounts
        except ClientError as e:
            print(f"Error getting existing accounts: {str(e)}")
            return []

    def create_user_accounts(self, email: str, workspace_ids: List[str],
                             as_admin: bool = False, dry_run: bool = True) -> bool:
        """Create accounts linking user to workspaces."""
        try:
            # Get user
            user = self.get_user_by_email(email)
            if not user:
                print(f"User with email {email} not found!")
                return False

            print(f"\nFound user: {user['id']} ({user['email']})")

            # Verify workspaces exist
            if not self.verify_workspaces_exist(workspace_ids):
                return False

            # Check for existing accounts
            existing_accounts = self.get_existing_accounts(user['id'], workspace_ids)
            if existing_accounts:
                print("\nWarning: Found existing accounts:")
                for acc in existing_accounts:
                    print(f"User already has access to workspace {acc['workspace_id']}")
                    print(f"Admin access: {acc['user_is_workspace_admin']}")

            # Create new accounts
            accounts_to_create = [
                ws_id for ws_id in workspace_ids
                if ws_id not in [acc['workspace_id'] for acc in existing_accounts]
            ]

            if not accounts_to_create:
                print("\nNo new accounts to create!")
                return True

            print(f"\nWill create {len(accounts_to_create)} new accounts:")
            for ws_id in accounts_to_create:
                print(f"Workspace: {ws_id}")
                print(f"Admin access: {as_admin}")

            if dry_run:
                print("\nDRY RUN - No accounts created")
                return True

            # Create accounts
            current_time = datetime.now().isoformat()
            for ws_id in accounts_to_create:
                account_id = generate_id('acc')
                self.tables['account'].put_item(Item={
                    'id': account_id,
                    'user_id': user['id'],
                    'workspace_id': ws_id,
                    'user_is_workspace_admin': as_admin,
                    'created_at': current_time,
                    'updated_at': current_time
                })
                print(f"Created account {account_id} for workspace {ws_id}")

            return True

        except Exception as e:
            print(f"Error creating accounts: {str(e)}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create accounts linking user to workspaces')
    parser.add_argument('email', help='Email of the user')
    parser.add_argument('workspace_ids', nargs='+', help='List of workspace IDs')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--as-admin', action='store_true', help='Create accounts with admin access')
    parser.add_argument('--execute', action='store_true', help='Actually create accounts (default is dry run)')

    args = parser.parse_args()

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"Creating accounts for {args.email}")
    print(f"Workspace IDs: {args.workspace_ids}")
    print(f"Admin access: {args.as_admin}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    if args.execute:
        confirm = input("Are you sure you want to create these accounts? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            exit(0)

    creator = UserAccountCreator(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage
    )

    if not creator.check_tables_exist():
        print("Required tables do not exist. Please check your configuration.")
        exit(1)

    success = creator.create_user_accounts(
        email=args.email,
        workspace_ids=args.workspace_ids,
        as_admin=args.as_admin,
        dry_run=not args.execute
    )

    if not success:
        exit(1)
