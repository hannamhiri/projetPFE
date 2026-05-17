from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.expectations.expectation_configuration import ExpectationConfiguration


def get_item_suite() -> ExpectationSuite:
    """Définit les règles de validation pour la table Item."""
    suite = ExpectationSuite(name="item_suite")

    # Id ne doit jamais être NULL
    suite.add_expectation(ExpectationConfiguration(
        type="expect_column_values_to_not_be_null",
        kwargs={"column": "Id"}
    ))

    # Id doit être unique
    suite.add_expectation(ExpectationConfiguration(
        type="expect_column_values_to_be_unique",
        kwargs={"column": "Id"}
    ))

    # Code ne doit jamais être NULL
    suite.add_expectation(ExpectationConfiguration(
        type="expect_column_values_to_not_be_null",
        kwargs={"column": "Code"}
    ))

    # Description ne doit jamais être NULL
    suite.add_expectation(ExpectationConfiguration(
        type="expect_column_values_to_not_be_null",
        kwargs={"column": "Description"}
    ))

    # IdProductItem ne doit plus avoir de NULL (remplacé par 408 avant)
    suite.add_expectation(ExpectationConfiguration(
        type="expect_column_values_to_not_be_null",
        kwargs={"column": "IdProductItem"}
    ))

    # Colonnes attendues exactement
    suite.add_expectation(ExpectationConfiguration(
        type="expect_table_columns_to_match_set",
        kwargs={"column_set": ["Id", "Code", "Description", "IdProductItem"]}
    ))

    return suite