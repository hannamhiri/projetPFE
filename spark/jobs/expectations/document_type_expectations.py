import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite


def get_document_type_suite(context, suite_name: str) -> ExpectationSuite:
    suite = ExpectationSuite(name=suite_name)
    try:
        suite = context.suites.add(suite)
    except Exception:
        context.suites.delete(suite_name)
        suite = context.suites.add(suite)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Code"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Label"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Code"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
    column="Code",regex=".*SA"))
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=["Code" ,"Label"]))

    return suite