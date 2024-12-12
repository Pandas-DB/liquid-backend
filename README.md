workspace-management/
├── package.json
├── package-lock.json
├── README.md
├── requirements-test.txt
├── requirements.txt
├── schema
│   ├── resolvers
│   │   ├── Mutation.bulkCreateData.req.vtl
│   │   ├── Mutation.bulkCreateData.res.vtl
│   │   ├── Mutation.createData.req.vtl
│   │   ├── Mutation.createData.res.vtl
│   │   ├── Mutation.createPath.req.vtl
│   │   ├── Mutation.deleteData.req.vtl
│   │   ├── Mutation.deleteData.res.vtl
│   │   ├── Query.listData.req.vtl
│   │   ├── Query.listData.res.vtl
│   │   ├── Query.listWorkspaces.req.vtl
│   │   └── Query.listWorkspaces.res.vtl
│   ├── schema_additions.graphql
│   └── schema.graphql
├── serverless.yml
├── src
│   ├── functions
│   │   ├── cascade_handlers
│   │   │   ├── cascade_delete.py
│   │   │   └── utils.py
│   │   └── data_handlers
│   │       ├── bulk_data_handler.py
│   │       ├── data_to_s3.py
│   │       └── utils.py
│   └── lib
│       └── common_utils.py
└── tests
    ├── functions
    │   ├── bulk_data_request.py
    │   └── client_test.py
    └── resolvers
