import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite


def get_item_suite(context, suite_name: str) -> ExpectationSuite:
    suite = ExpectationSuite(name=suite_name)
    #suite = context.suites.add(suite)
    try:
        suite = context.suites.add(suite)
    except Exception:
        context.suites.delete(suite_name)
        suite = context.suites.add(suite)

    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdProductItem"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdFamily"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Code"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Label"))

    #doit contenir au moins un caractère alphanumérique (n'importe où)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
    column="Label",
    regex=".*[a-zA-Z0-9].*",
    row_condition="Label.notna()",
    condition_parser="pandas"
))
    #doit commencer par un caractère alphanumérique
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
    column="Code",
    regex=".*[a-zA-Z0-9].*",
    row_condition="Code.notna()",
    condition_parser="pandas"
))

    #suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdProductItem"))
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=["Id", "Code", "Label", "IdProductItem","IdFamily"]
    ))

    return suite
