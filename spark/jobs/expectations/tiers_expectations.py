import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite


def get_tiers_suite(context, suite_name: str) -> ExpectationSuite:
    suite = ExpectationSuite(name=suite_name)
    try:
        suite = context.suites.add(suite)
    except Exception:
        context.suites.delete(suite_name)
        suite = context.suites.add(suite)

   
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdGeographicalArea"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Id"))

    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Name"))
     #doit contenir au moins un caractère alphanumérique (n'importe où)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
    column="Name",
    regex=".*[a-zA-Z0-9].*",
    row_condition="Name.notna()",
    condition_parser="pandas"
))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Code"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IsBTOB"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IsActive"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
    column="IsBTOB",
    value_set=[0, 1]  
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
    column="IsActive",
    value_set=[0, 1]   
    ))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
    column="Code",regex="^C-.*"))
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=["Id", "Code" ,"Name", "IdGeographicalArea", "IsBTOB", "IsActive"]
    ))

    return suite