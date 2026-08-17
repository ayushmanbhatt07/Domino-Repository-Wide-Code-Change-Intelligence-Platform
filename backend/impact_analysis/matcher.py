class ImpactMatcher:

    def __init__(self, graph_store):
        self.graph_store = graph_store

    def match(
        self,
        repo: str,
        file_name=None,
        function_name=None,
        class_name=None,
        route=None,
    ):
        supplied = [
            ("file", file_name),
            ("function", function_name),
            ("class", class_name),
            ("route", route),
        ]

        supplied = [
            (entity_type, value)
            for entity_type, value in supplied
            if value is not None
        ]

        if len(supplied) == 0:
            raise ValueError(
                "At least one of file_name, function_name, "
                "class_name, or route must be provided."
            )

        if len(supplied) > 1:
            raise ValueError(
                "Provide only one changed entity at a time."
            )

        entity_type, value = supplied[0]

        entity = self.graph_store.find_entity(
            repo=repo,
            entity_type=entity_type,
            name=value
        )

        if entity is None:
            raise ValueError(
                f"{entity_type} '{value}' was not found "
                f"in repository '{repo}'."
            )

        return entity