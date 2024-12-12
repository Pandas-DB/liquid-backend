"""run example:
python3 scripts/admin/promote_user_accounts.py admin@test.com ws-uuid-1 ws-uuid-2 ws-uuid-3 --aws-profile test --stage dev --execute
"""


import os
import boto3
import argparse
from typing import Optional, List, Dict, Tuple
from botocore.exceptions import ClientError
from datetime import datetime


class UserAccountPromoter:
    def __init__(self, region: str = 'eu-west-1', profile: Optional[str] = None, stage: str = 'dev'):
        # Setup AWS session
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.dynamodb = session.resource('dynamodb', region_name=region)

        # Initialize table names
        prefix = f"workspace-management-{stage}"
        self.table_names = {
            'user': f"{prefix}-user",
            'account': f"{prefix}-account",
            'workspace': f"{prefix}-workspace"
        }

        # Initialize table references
        self.tables = {
            name: self.dynamodb.Table(table_name)
            for name, table_name in self.table_names.items()
        }

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

    def get_account_status(self, user_id: str, workspace_ids: List[str]) -> List[Tuple[str, Optional[Dict]]]:
        """Get account status for each workspace.
        Returns list of tuples (workspace_id, account_dict or None)"""
        status = []
        try:
            for ws_id in workspace_ids:
                response = self.tables['account'].scan(
                    FilterExpression='user_id = :uid AND workspace_id = :wsid',
                    ExpressionAttributeValues={
                        ':uid': user_id,
                        ':wsid': ws_id
                    }
                )
                account = response['Items'][0] if response['Items'] else None
                status.append((ws_id, account))
        except ClientError as e:
            print(f"Error getting account status: {str(e)}")
        return status

    def promote_user_accounts(self, email: str, workspace_ids: List[str], dry_run: bool = True) -> bool:
        """Promote user accounts to admin for specified workspaces."""
        try:
            # Verify user exists
            user = self.get_user_by_email(email)
            if not user:
                print(f"User with email {email} not found!")
                return False

            print(f"\nFound user: {user['id']} ({user['email']})")

            # Get account status for each workspace
            account_status = self.get_account_status(user['id'], workspace_ids)

            # Group accounts by status
            no_account = []
            already_admin = []
            to_promote = []

            for ws_id, account in account_status:
                if not account:
                    no_account.append(ws_id)
                elif account['user_is_workspace_admin']:
                    already_admin.append(ws_id)
                else:
                    to_promote.append(account)

            # Report status
            if no_account:
                print("\nWorkspaces where user has no account (will be skipped):")
                for ws_id in no_account:
                    print(f"- {ws_id}")

            if already_admin:
                print("\nWorkspaces where user is already admin (will be skipped):")
                for ws_id in already_admin:
                    print(f"- {ws_id}")

            if to_promote:
                print("\nAccounts to be promoted to admin:")
                for account in to_promote:
                    print(f"- Workspace: {account['workspace_id']}")
                    print(f"  Account ID: {account['id']}")
            else:
                print("\nNo accounts to promote!")
                return True

            if dry_run:
                print("\nDRY RUN - No changes made")
                return True

            # Perform promotions
            current_time = datetime.now().isoformat()
            for account in to_promote:
                self.tables['account'].update_item(
                    Key={'id': account['id']},
                    UpdateExpression='SET user_is_workspace_admin = :admin, updated_at = :time',
                    ExpressionAttributeValues={
                        ':admin': True,
                        ':time': current_time
                    }
                )
                print(f"\nPromoted account {account['id']} to admin for workspace {account['workspace_id']}")

            print("\nPromotion completed successfully!")
            return True

        except Exception as e:
            print(f"Error promoting accounts: {str(e)}")
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Promote user accounts to admin status')
    parser.add_argument('email', help='Email of the user')
    parser.add_argument('workspace_ids', nargs='+', help='List of workspace IDs to promote admin access')
    parser.add_argument('--stage', default='dev', help='Stage (dev, prod, etc)')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--aws-profile', default='test', help='AWS profile name')
    parser.add_argument('--execute', action='store_true', help='Actually perform promotions (default is dry run)')

    args = parser.parse_args()

    print(f"\nUsing AWS Profile: {args.aws_profile}")
    print(f"Region: {args.region}")
    print(f"Stage: {args.stage}")
    print(f"User: {args.email}")
    print(f"Workspace IDs: {args.workspace_ids}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}\n")

    if args.execute:
        confirm = input("Are you sure you want to promote these accounts to admin status? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled")
            exit(0)

    promoter = UserAccountPromoter(
        region=args.region,
        profile=args.aws_profile,
        stage=args.stage
    )

    success = promoter.promote_user_accounts(
        args.email,
        args.workspace_ids,
        dry_run=not args.execute
    )

    if not success:
        exit(1)
