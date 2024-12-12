# Liquid Backend

This repository contains a serverless application designed to handle data processing tasks, user account management, and GraphQL schema management. Below is a detailed breakdown of the project structure.

## Project Structure

```
├── build-layer.sh                 # Script to build dependencies layer for AWS Lambda
├── package.json                   # Node.js package configuration file
├── package-lock.json              # Dependency lock file
├── README.md                      # Project documentation (this file)
├── requirements-lambda.txt        # Python dependencies for Lambda functions
├── requirements-test.txt          # Python dependencies for testing
├── requirements.txt               # General Python dependencies
├── schema                         # GraphQL schema and resolvers
│   ├── resolvers                  # VTL files for GraphQL mutations and queries
│   │   ├── Mutation.bulkCreateData.req.vtl
│   │   ├── Mutation.bulkCreateData.res.vtl
│   │   ├── Mutation.createComponent.req.vtl
│   │   ├── Mutation.createComponent.res.vtl
│   │   ├── Mutation.createData.req.vtl
│   │   ├── Mutation.createData.res.vtl
│   │   ├── Mutation.createPath.req.vtl
│   │   ├── Mutation.deleteComponent.req.vtl
│   │   ├── Mutation.deleteComponent.res.vtl
│   │   ├── Mutation.deleteData.req.vtl
│   │   ├── Mutation.deleteData.res.vtl
│   │   ├── Query.listData.req.vtl
│   │   ├── Query.listData.res.vtl
│   │   ├── Query.listWorkspaces.req.vtl
│   │   └── Query.listWorkspaces.res.vtl
│   ├── schema_additions.graphql   # Additional GraphQL schema definitions
│   └── schema.graphql             # Main GraphQL schema file
├── scripts                        # Administrative scripts for maintenance
│   └── admin
│       ├── cleanup_orphan_workspaces.py
│       ├── create_user_accounts.py
│       ├── create_user.py
│       ├── delete_user_accounts.py
│       ├── delete_user_cascade.py
│       ├── delete_workspace_cascade.py
│       └── promote_user_accounts.py
├── serverless.yml                 # Serverless framework configuration
├── src                            # Source code for application logic
│   ├── functions
│   │   ├── cascade_handlers       # Cascade-related handlers
│   │   │   ├── cascade_delete.py
│   │   │   └── utils.py
│   │   └── data_handlers          # Data-related handlers
│   │       ├── bulk_data_handler.py
│   │       ├── bulk_get_data_handler.py
│   │       ├── data_to_s3.py
│   │       └── utils.py
│   └── lib
│       └── common_utils.py        # Common utility functions
└── tests                          # Unit tests for the application
    ├── functions
    │   ├── bulk_data_request.py
    │   └── client_test.py
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
- **Serverless Framework**: The `serverless.yml` file configures the deployment of the application, including Lambda functions, triggers, and resources.

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

## Testing

## Contribution
Feel free to contribute by creating issues or submitting pull requests. Please adhere to the coding guidelines outlined in the contribution guide (if available).

## License
This project is licensed under [License Name].

