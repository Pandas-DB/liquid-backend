workspace-management/
├── README.md
├── package.json
├── requirements.txt
├── serverless.yml
├── schema/
│   ├── schema.graphql
│   └── resolvers/
│       ├── Mutation.createData.req.vtl
│       ├── Mutation.createData.res.vtl
│       ├── Mutation.deleteData.req.vtl
│       ├── Mutation.deleteData.res.vtl
│       ├── Query.listData.req.vtl
│       └── Query.listData.res.vtl
├── src/
│   ├── functions/
│   │   ├── data_handlers/
│   │   │   ├── __init__.py
│   │   │   ├── data_to_s3.py
│   │   │   └── utils.py
│   │   └── cascade_handlers/
│   │       ├── __init__.py
│   │       ├── cascade_delete.py
│   │       └── utils.py
│   └── lib/
│       ├── __init__.py
│       └── common_utils.py
├── infrastructure/
│   ├── dynamo-tables.yml
│   └── s3-resources.yml
└── tests/
    ├── functions/
    │   ├── test_data_to_s3.py
    │   └── test_cascade_delete.py
    └── resolvers/
        └── test_data_mutations.py
