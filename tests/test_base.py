from pytest import raises
import json

from graphql_server import (
    json_encode,
    load_json_body,
    run_http_query,
    GraphQLParams,
    HttpQueryError,
)
from .schema import schema


def test_allows_get_with_query_param():
    query = "{test}"
    results, params = run_http_query(schema, "get", {}, query_data=dict(query=query))

    assert results == [({"test": "Hello World"}, None)]
    assert params == [GraphQLParams(query=query, variables=None, operation_name=None)]


def test_allows_get_with_variable_values():
    results, params = run_http_query(
        schema,
        "get",
        {},
        query_data=dict(
            query="query helloWho($who: String){ test(who: $who) }",
            variables=json.dumps({"who": "Dolly"}),
        ),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_allows_get_with_operation_name():
    results, params = run_http_query(
        schema,
        "get",
        {},
        query_data=dict(
            query="""
        query helloYou { test(who: "You"), ...shared }
        query helloWorld { test(who: "World"), ...shared }
        query helloDolly { test(who: "Dolly"), ...shared }
        fragment shared on QueryRoot {
          shared: test(who: "Everyone")
        }
        """,
            operationName="helloWorld",
        ),
    )

    assert results == [({"test": "Hello World", "shared": "Hello Everyone"}, None)]


def test_reports_validation_errors():
    results, params = run_http_query(
        schema, "get", {}, query_data=dict(query="{ test, unknownOne, unknownTwo }")
    )

    assert results == [
        (
            None,
            [
                {
                    "message": "Cannot query field 'unknownOne' on type 'QueryRoot'.",
                    "locations": [(1, 9)],
                },
                {
                    "message": "Cannot query field 'unknownTwo' on type 'QueryRoot'.",
                    "locations": [(1, 21)],
                },
            ],
        )
    ]


def test_errors_when_missing_operation_name():
    results, params = run_http_query(
        schema,
        "get",
        {},
        query_data=dict(
            query="""
        query TestQuery { test }
        mutation TestMutation { writeTest { test } }
        """
        ),
    )

    assert results == [
        (
            None,
            [
                {
                    "message": (
                        "Must provide operation name"
                        " if query contains multiple operations."
                    )
                }
            ],
        )
    ]
    assert results[0].errors[0].__class__.__name__ == 'GraphQLError'


def test_errors_when_sending_a_mutation_via_get():
    with raises(HttpQueryError) as exc_info:
        run_http_query(
            schema,
            "get",
            {},
            query_data=dict(
                query="""
                mutation TestMutation { writeTest { test } }
                """
            ),
        )

    assert exc_info.value == HttpQueryError(
        405,
        "Can only perform a mutation operation from a POST request.",
        headers={"Allow": "POST"},
    )


def test_errors_when_selecting_a_mutation_within_a_get():
    with raises(HttpQueryError) as exc_info:
        run_http_query(
            schema,
            "get",
            {},
            query_data=dict(
                query="""
                query TestQuery { test }
                mutation TestMutation { writeTest { test } }
                """,
                operationName="TestMutation",
            ),
        )

    assert exc_info.value == HttpQueryError(
        405,
        "Can only perform a mutation operation from a POST request.",
        headers={"Allow": "POST"},
    )


def test_allows_mutation_to_exist_within_a_get():
    results, params = run_http_query(
        schema,
        "get",
        {},
        query_data=dict(
            query="""
            query TestQuery { test }
            mutation TestMutation { writeTest { test } }
            """,
            operationName="TestQuery",
        ),
    )

    assert results == [({"test": "Hello World"}, None)]


def test_allows_post_with_json_encoding():
    result = load_json_body('{"query": "{test}"}')
    assert result == {"query": "{test}"}


def test_allows_sending_a_mutation_via_post():
    results, params = run_http_query(
        schema,
        "post",
        {},
        query_data=dict(query="mutation TestMutation { writeTest { test } }"),
    )

    assert results == [({"writeTest": {"test": "Hello World"}}, None)]


def test_allows_post_with_url_encoding():
    results, params = run_http_query(
        schema, "post", {}, query_data=dict(query="{test}")
    )

    assert results == [({"test": "Hello World"}, None)]


def test_supports_post_json_query_with_string_variables():
    results, params = run_http_query(
        schema,
        "post",
        {},
        query_data=dict(
            query="query helloWho($who: String){ test(who: $who) }",
            variables='{"who": "Dolly"}',
        ),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_supports_post_json_query_with_json_variables():
    result = load_json_body(
        """
        {
            "query": "query helloWho($who: String){ test(who: $who) }",
            "variables": {"who": "Dolly"}
        }
        """
    )

    assert result["variables"] == {"who": "Dolly"}


def test_supports_post_url_encoded_query_with_string_variables():
    results, params = run_http_query(
        schema,
        "post",
        {},
        query_data=dict(
            query="query helloWho($who: String){ test(who: $who) }",
            variables='{"who": "Dolly"}',
        ),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_supports_post_json_query_with_get_variable_values():
    results, params = run_http_query(
        schema,
        "post",
        data=dict(query="query helloWho($who: String){ test(who: $who) }"),
        query_data=dict(variables={"who": "Dolly"}),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_post_url_encoded_query_with_get_variable_values():
    results, params = run_http_query(
        schema,
        "get",
        data=dict(query="query helloWho($who: String){ test(who: $who) }"),
        query_data=dict(variables='{"who": "Dolly"}'),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_supports_post_raw_text_query_with_get_variable_values():
    results, params = run_http_query(
        schema,
        "get",
        data=dict(query="query helloWho($who: String){ test(who: $who) }"),
        query_data=dict(variables='{"who": "Dolly"}'),
    )

    assert results == [({"test": "Hello Dolly"}, None)]


def test_allows_post_with_operation_name():
    results, params = run_http_query(
        schema,
        "get",
        data=dict(
            query="""
            query helloYou { test(who: "You"), ...shared }
            query helloWorld { test(who: "World"), ...shared }
            query helloDolly { test(who: "Dolly"), ...shared }
            fragment shared on QueryRoot {
              shared: test(who: "Everyone")
            }
            """,
            operationName="helloWorld",
        ),
    )

    assert results == [({"test": "Hello World", "shared": "Hello Everyone"}, None)]


def test_allows_post_with_get_operation_name():
    results, params = run_http_query(
        schema,
        "get",
        data=dict(
            query="""
            query helloYou { test(who: "You"), ...shared }
            query helloWorld { test(who: "World"), ...shared }
            query helloDolly { test(who: "Dolly"), ...shared }
            fragment shared on QueryRoot {
              shared: test(who: "Everyone")
            }
            """
        ),
        query_data=dict(operationName="helloWorld"),
    )

    assert results == [({"test": "Hello World", "shared": "Hello Everyone"}, None)]


def test_supports_pretty_printing_data():
    results, params = run_http_query(schema, "get", data=dict(query="{test}"))
    result = {"data": results[0].data}

    assert json_encode(result, pretty=True) == (
        "{\n" '  "data": {\n' '    "test": "Hello World"\n' "  }\n" "}"
    )


def test_not_pretty_data_by_default():
    results, params = run_http_query(schema, "get", data=dict(query="{test}"))
    result = {"data": results[0].data}

    assert json_encode(result) == '{"data":{"test":"Hello World"}}'


def test_handles_field_errors_caught_by_graphql():
    results, params = run_http_query(schema, "get", data=dict(query="{thrower}"))

    assert results == [
        (None, [{"message": "Throws!", "locations": [(1, 2)], "path": ["thrower"]}])
    ]


def test_handles_syntax_errors_caught_by_graphql():
    results, params = run_http_query(schema, "get", data=dict(query="syntaxerror"))

    assert results == [
        (
            None,
            [
                {
                    "locations": [(1, 1)],
                    "message": "Syntax Error: Unexpected Name 'syntaxerror'",
                }
            ],
        )
    ]


def test_handles_errors_caused_by_a_lack_of_query():
    with raises(HttpQueryError) as exc_info:
        run_http_query(schema, "get", {})

    assert exc_info.value == HttpQueryError(400, "Must provide query string.")


def test_handles_errors_caused_by_invalid_query_type():
    results, params = run_http_query(schema, "get", dict(query=42))

    assert results == [(None, [{'message': 'Must provide Source. Received: 42'}])]


def test_handles_batch_correctly_if_is_disabled():
    with raises(HttpQueryError) as exc_info:
        run_http_query(schema, "post", [])

    assert exc_info.value == HttpQueryError(
        400, "Batch GraphQL requests are not enabled."
    )


def test_handles_incomplete_json_bodies():
    with raises(HttpQueryError) as exc_info:
        load_json_body('{"query":')

    assert exc_info.value == HttpQueryError(400, "POST body sent invalid JSON.")


def test_handles_plain_post_text():
    with raises(HttpQueryError) as exc_info:
        run_http_query(schema, "post", {})

    assert exc_info.value == HttpQueryError(400, "Must provide query string.")


def test_handles_poorly_formed_variables():
    with raises(HttpQueryError) as exc_info:
        run_http_query(
            schema,
            "get",
            {},
            query_data=dict(
                query="query helloWho($who: String){ test(who: $who) }",
                variables="who:You",
            ),
        )

    assert exc_info.value == HttpQueryError(400, "Variables are invalid JSON.")


def test_handles_unsupported_http_methods():
    with raises(HttpQueryError) as exc_info:
        run_http_query(schema, "put", {})

    assert exc_info.value == HttpQueryError(
        405,
        "GraphQL only supports GET and POST requests.",
        headers={"Allow": "GET, POST"},
    )


def test_passes_request_into_request_context():
    results, params = run_http_query(
        schema,
        "get",
        {},
        query_data=dict(query="{request}"),
        context_value={"q": "testing"},
    )

    assert results == [({"request": "testing"}, None)]


def test_supports_pretty_printing_context():
    class Context:
        def __str__(self):
            return "CUSTOM CONTEXT"

    results, params = run_http_query(
        schema, "get", {}, query_data=dict(query="{context}"), context_value=Context()
    )

    assert results == [({"context": "CUSTOM CONTEXT"}, None)]


def test_post_multipart_data():
    query = "mutation TestMutation { writeTest { test } }"
    results, params = run_http_query(schema, "post", {}, query_data=dict(query=query))

    assert results == [({"writeTest": {"test": "Hello World"}}, None)]


def test_batch_allows_post_with_json_encoding():
    data = load_json_body('[{"query": "{test}"}]')
    results, params = run_http_query(schema, "post", data, batch_enabled=True)

    assert results == [({"test": "Hello World"}, None)]


def test_batch_supports_post_json_query_with_json_variables():
    data = load_json_body(
        '[{"query":"query helloWho($who: String){ test(who: $who) }",'
        '"variables":{"who":"Dolly"}}]'
    )
    results, params = run_http_query(schema, "post", data, batch_enabled=True)

    assert results == [({"test": "Hello Dolly"}, None)]


def test_batch_allows_post_with_operation_name():
    data = [
        dict(
            query="""
            query helloYou { test(who: "You"), ...shared }
            query helloWorld { test(who: "World"), ...shared }
            query helloDolly { test(who: "Dolly"), ...shared }
            fragment shared on QueryRoot {
              shared: test(who: "Everyone")
            }
            """,
            operationName="helloWorld",
        )
    ]
    data = load_json_body(json_encode(data))
    results, params = run_http_query(schema, "post", data, batch_enabled=True)

    assert results == [({"test": "Hello World", "shared": "Hello Everyone"}, None)]
