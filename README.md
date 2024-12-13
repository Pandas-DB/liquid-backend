# Liquid Backend

This repository contains a serverless application designed to handle data processing tasks, user account management, and GraphQL schema management. Below is a detailed breakdown of the project structure.

## Project Structure

```
├── build-layer.sh
├── package.json
├── package-lock.json
├── README.md
├── requirements-lambda.txt
├── requirements-test.txt
├── requirements.txt
├── serverless.yml
├── serverless-indexes.yml
├── schema
│   ├── resolvers
│   │   ├── Mutation.bulkCreateData.req.vtl
│   │   ├── Mutation.bulkCreateData.res.vtl
│   │   ├── Mutation.createComponent.req.vtl
│   │   ├── Mutation.createComponent.res.vtl
│   │   ├── Mutation.createData.req.vtl
│   │   ├── Mutation.createData.res.vtl
│   │   ├── Mutation.createPath.req.vtl
│   │   ├── Mutation.createPath.res.vtl
│   │   ├── Mutation.createWorkspaces.req.vtl
│   │   ├── Mutation.createWorkspaces.res.vtl
│   │   ├── Mutation.deleteComponent.req.vtl
│   │   ├── Mutation.deleteComponent.res.vtl
│   │   ├── Mutation.deleteData.req.vtl
│   │   ├── Mutation.deleteData.res.vtl
│   │   ├── Mutation.deletePath.req.vtl
│   │   ├── Mutation.deletePath.res.vtl
│   │   ├── Mutation.deleteWorkspaces.req.vtl
│   │   ├── Mutation.deleteWorkspaces.res.vtl
│   │   ├── Query.getComponent.req.vtl
│   │   ├── Query.getComponent.res.vtl
│   │   ├── Query.getData.req.vtl
│   │   ├── Query.getData.res.vtl
│   │   ├── Query.getPath.req.vtl
│   │   ├── Query.getPath.res.vtl
│   │   ├── Query.getWorkspaces.req.vtl
│   │   ├── Query.getWorkspaces.res.vtl
│   │   ├── Query.listComponents.req.vtl
│   │   ├── Query.listComponents.res.vtl
│   │   ├── Query.listData.req.vtl
│   │   ├── Query.listData.res.vtl
│   │   ├── Query.listPath.req.vtl
│   │   ├── Query.listPath.res.vtl
│   │   ├── Query.listWorkspaces.req.vtl
│   │   └── Query.listWorkspaces.res.vtl
│   ├── schema_additions.graphql
│   └── schema.graphql
├── scripts
│   └── admin
│       ├── cleanup_orphan_workspaces.py
│       ├── create_user_accounts.py
│       ├── create_user.py
│       ├── delete_user_accounts.py
│       ├── delete_user_cascade.py
│       ├── delete_workspace_cascade.py
│       └── promote_user_accounts.py
├── src
│   ├── functions
│   │   ├── cascade_handlers
│   │   │   ├── cascade_delete.py
│   │   │   └── utils.py
│   │   └── data_handlers
│   │       ├── data_to_s3.py
│   │       ├── get_component_data.py
│   │       ├── get_path_components.py
│   │       ├── get_workspace_paths.py
│   │       ├── post_bulk_data_handler.py
│   │       └── utils.py
│   └── lib
│       └── common_utils.py
└── tests
    ├── functions
    │   ├── bulk_post_data_request.py
    │   ├── client_test.py
    │   ├── get_component_data_request.py
    │   ├── get_path_components_request.py
    │   └── get_workspace_paths_request.py
    └── resolvers
```

## Key Components

### Schema
- **GraphQL Schema**: Located in the `schema` folder, this directory contains the main schema definition and resolver files written in VTL (Velocity Template Language).
- **Resolvers**: Handle GraphQL queries and mutations, including bulk data operations, component creation, and workspace listing.

### Scripts
- **Administrative Scripts**: Found in the `scripts/admin` folder, these Python scripts handle tasks like cleaning up orphaned workspaces, managing user accounts, and promoting users.

### Source Code
- **Functions**: The `src/functions` folder contains logic for handling cascade deletions, data operations, and utility functions.
- **Common Utilities**: Shared utilities are located in `src/lib/common_utils.py`.

### Testing
- **Unit Tests**: The `tests` folder includes Python test files to validate functionality for both functions and resolvers.

### Configuration
- **Serverless Framework**: 
  - The `serverless.yml` file configures the deployment of the application, including Lambda functions, triggers, and resources.
  - `serverless-indexes.yml` complements (must be run afterwards) the configuration adding further `GlobalSecondaryIndexes` to DynamoDB

## Getting Started

### Prerequisites
- **Node.js**: Install Node.js for managing dependencies and running scripts.
- **Python**: Install Python for running scripts and Lambda functions.
- **Serverless Framework**: Install the Serverless framework for deploying the application.

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   ```
2. Install Node.js dependencies:
   ```bash
   npm install
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Deployment

```bash
   serverless deploy
   serverless deploy serverless-indexes.yml
```

## Testing

## Contribution
Feel free to contribute by creating issues or submitting pull requests. Please adhere to the coding guidelines outlined in the contribution guide (if available).

## License
This project is licensed under [License Name].

