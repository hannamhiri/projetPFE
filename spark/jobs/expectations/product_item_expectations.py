import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite


def get_product_item_suite(context, suite_name: str) -> ExpectationSuite:
    suite = ExpectationSuite(name=suite_name)
    try:
        suite = context.suites.add(suite)
    except Exception:
        context.suites.delete(suite_name)
        suite = context.suites.add(suite)

    # Id ne doit jamais être NULL
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Id"))

    # Id doit être unique
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Id"))

    # LabelProduct ne doit pas être NULL
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="LabelProduct"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="CodeProduct"))

    # LabelProduct doit contenir au moins un alphanumérique
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
        column="LabelProduct",
        regex = "^[a-zA-Z0-9\\u00C0-\\u024F].*",
        row_condition="LabelProduct.notna()",
        condition_parser="pandas"
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
        column="CodeProduct",
        regex = "^[a-zA-Z0-9\\u00C0-\\u024F].*",
        row_condition="CodeProduct.notna()",
        condition_parser="pandas"
    ))

    # Colonnes attendues exactement
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=["Id", "CodeProduct" ,"LabelProduct"]
    ))

    return suite