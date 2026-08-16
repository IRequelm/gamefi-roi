from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import app.engine.calculator as calculator
import app.engine.inputs as engine_inputs
from app.adapters.contract import ADAPTER_CONTRACT_VERSION, AdapterResultV1, StrategyAdapterV1, ValueClassification
from app.adapters.defi_kingdoms_jeweler import DfkJewelerAdapter
from app.adapters.farmers_world import FarmersWorldAxeAdapter
from app.adapters.splinterlands import SplinterlandsModernRankedAdapter
from app.strategies.defi_kingdoms import DFK_CJEWEL_MAX_LOCK_V1
from app.strategies.farmers_world import FARMERS_WORLD_AXE_WOOD_V1
from app.strategies.splinterlands import SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1
from test_dfk_jeweler_adapter import FIXTURE_PATH as DFK_FIXTURE_PATH
from test_dfk_jeweler_adapter import _observations_from_fixture as dfk_observations
from test_farmers_world_adapter import FIXTURE_PATH as FARMERS_FIXTURE_PATH
from test_farmers_world_adapter import _observations_from_fixture as farmers_observations
from test_splinterlands_adapter import FIXTURE_PATH as SPLINTERLANDS_FIXTURE_PATH
from test_splinterlands_adapter import _observations_from_fixture as splinterlands_observations


@pytest.mark.parametrize(
    ("adapter", "fixture_path", "observation_builder", "expects_uncertainty"),
    (
        (DfkJewelerAdapter(DFK_CJEWEL_MAX_LOCK_V1), DFK_FIXTURE_PATH, dfk_observations, False),
        (FarmersWorldAxeAdapter(FARMERS_WORLD_AXE_WOOD_V1), FARMERS_FIXTURE_PATH, farmers_observations, False),
        (
            SplinterlandsModernRankedAdapter(SPLINTERLANDS_MODERN_RANKED_SPS_EV_V1),
            SPLINTERLANDS_FIXTURE_PATH,
            splinterlands_observations,
            True,
        ),
    ),
)
def test_existing_adapters_conform_to_adapter_contract_v1(
    adapter: StrategyAdapterV1,
    fixture_path: Path,
    observation_builder,
    expects_uncertainty: bool,
) -> None:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    observations = observation_builder(fixture["strategy"])

    assert isinstance(adapter, StrategyAdapterV1)
    result = adapter.build_engine_input(
        observations,
        calculated_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
    )

    assert isinstance(result, AdapterResultV1)
    assert result.contract_version == ADAPTER_CONTRACT_VERSION
    assert result.economics_input.strategy_id
    assert result.economics_input.strategy_version
    assert result.economics_input.model_version
    assert result.economics_input.reporting_currency == "USD"
    assert result.economics_input.input_observation_ids
    assert result.classifications
    assert set(result.derived_values).issubset(set(result.classifications))
    for metric in result.derived_values:
        assert result.classifications[metric] == ValueClassification.DERIVED
    for observation in observations:
        if observation.observation_id in result.economics_input.input_observation_ids:
            assert observation.metric in result.classifications
    assert all(isinstance(classification, ValueClassification) for classification in result.classifications.values())

    if expects_uncertainty:
        assert result.warnings
        assert result.uncertainty_ranges
        for metric_range in result.uncertainty_ranges.values():
            low = result.derived_values[metric_range.low_metric]
            base = result.derived_values[metric_range.base_metric]
            high = result.derived_values[metric_range.high_metric]
            assert low <= base <= high
    else:
        assert result.warnings == ()
        assert result.uncertainty_ranges == {}


def test_roi_engine_remains_free_of_game_specific_adapter_assumptions() -> None:
    engine_source = f"{inspect.getsource(calculator)}\n{inspect.getsource(engine_inputs)}".lower()

    for forbidden in ("dfk", "defi_kingdoms", "farmers_world", "splinterlands", "jewel", "fww", "sps"):
        assert forbidden not in engine_source
