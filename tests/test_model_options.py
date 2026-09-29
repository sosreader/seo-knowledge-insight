import pytest

from utils.model_options import reasoning_options


@pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-6-sol"])
def test_migrated_models_preserve_none_effort(model):
    assert reasoning_options(model) == {"reasoning_effort": "none"}


@pytest.mark.parametrize("model", ["gpt-5.4-nano", "gpt-5.4", "custom-model", "gpt-6-astra"])
def test_other_models_keep_their_existing_parameters(model):
    assert reasoning_options(model) == {}
