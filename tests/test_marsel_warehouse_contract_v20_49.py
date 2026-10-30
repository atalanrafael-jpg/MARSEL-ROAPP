from pathlib import Path
import importlib.util


SCRIPT = Path(__file__).parents[1] / "scripts" / "marsel_warehouse_contract_v20_48.py"
SPEC = importlib.util.spec_from_file_location("marsel_warehouse_contract", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_warehouse_contract_uses_exact_documented_v2_endpoint():
    assert MODULE.API_ROOT == "https://api.roapp.io"
    assert MODULE.DOCUMENTED_PATH == "/v2/warehouse/"
    assert f"{MODULE.API_ROOT}{MODULE.DOCUMENTED_PATH}" == "https://api.roapp.io/v2/warehouse/"


def test_warehouse_contract_probes_only_documented_type_values():
    assert MODULE.PROBE_TYPES == ("product", "asset")


def test_warehouse_collection_is_complete_only_when_count_matches_data_length():
    valid = {"http": 200, "json_valid": True, "data_is_list": True, "data_count": 11, "count": 11}
    incomplete = {"http": 200, "json_valid": True, "data_is_list": True, "data_count": 10, "count": 11}
    assert MODULE.is_complete_list_response(valid) is True
    assert MODULE.is_complete_list_response(incomplete) is False


def test_empty_but_complete_warehouse_collection_is_valid():
    empty = {"http": 200, "json_valid": True, "data_is_list": True, "data_count": 0, "count": 0}
    assert MODULE.is_complete_list_response(empty) is True


def test_warehouse_diagnostic_is_read_only():
    assert MODULE.DOC.endswith("/reference/get-warehouses")
    assert "WRITE" not in MODULE.DOCUMENTED_PATH.upper()
