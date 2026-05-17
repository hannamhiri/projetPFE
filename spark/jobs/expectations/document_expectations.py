import great_expectations as gx
from great_expectations.core.expectation_suite import ExpectationSuite

def get_document_suite(context, suite_name: str) -> ExpectationSuite:
    suite = ExpectationSuite(name=suite_name)
    try:
        suite = context.suites.add(suite)
    except Exception:
        context.suites.delete(suite_name)
        suite = context.suites.add(suite)

    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="Id"))

    # Code — format alphanumérique avec tirets
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="Code"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
        column="Code",
        regex="^[a-zA-Z0-9\u00C0-\u024F].*",
        row_condition="Code.notna()",
        condition_parser="pandas"
    ))

    # IdDocumentStatus — doit être renseigné
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdDocumentStatus"))

    # DocumentTypeCode — format X-XX (ex: D-SA, I-SA, D-PU)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="DocumentTypeCode"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToMatchRegex(
        column="DocumentTypeCode",
        regex="^([A-Z]{1}|[A-Z]{2})-[A-Z]{2}$",
        row_condition="DocumentTypeCode.notna()",
        condition_parser="pandas"
    ))

    # IdTiers — clé étrangère obligatoire
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="IdTiers"))

    # DocumentDate — doit être renseignée
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="DocumentDate"))


    # IsForPos — booléen, peut être NULL (vu dans les données)
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeInSet(
        column="IsForPos",
        value_set=[0, 1]
    ))

    # Colonnes attendues
    suite.add_expectation(gx.expectations.ExpectTableColumnsToMatchSet(
        column_set=["Id", "Code", "IdDocumentStatus", "DocumentTypeCode",
                    "IdTiers", "DocumentDate", "IsForPos"]
    ))

    return suite