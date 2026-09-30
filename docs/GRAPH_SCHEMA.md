# Graph Schema

All nodes share the `repo` property to ensure multi-repo isolation, and an `id` property which uniquely identifies the node within that repo.

## Nodes
- **`(:Repo)`**: Metadata node describing a repository footprint (`name`, `commit_sha`, `node_count`, `edge_count`).
- **`(:File)`**: A source code file (`id="file:{path}"`, `path`).
- **`(:Class)`**: A class definition (`id="class:{path}:{qualified_name}"`, `name`, `qualified_name`, `path`).
- **`(:Function)`**: A function or method (`id="function:{path}:{qualified_name}"`, `name`, `qualified_name`, `path`, `is_test`, `is_async`).
- **`(:Route)`**: An API endpoint route (`id="route:{method}:{path}"`, `method`, `path`).
- **`(:External)`**: A library or external function call (`id="external:{name}"`, `name`).

## Edges
- **`CONTAINS`**: `File -> Class`, `File -> Function`, `Class -> Function`
- **`CALLS`**: `Function -> Function/Class/External` (with properties `confidence`, `resolution`, `line`)
- **`HANDLED_BY`**: `Route -> Function`
- **`INHERITS`**: `Class -> Class`
- **`IMPORTS`**: `File -> File`
- **`REFERENCES`**: `Function -> Class` (typing refs)
- **`EXERCISES`**: `Function -> Route` (API Client calls inside tests)
