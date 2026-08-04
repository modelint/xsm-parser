""" test_state_table.py - the markdown state transition table generated from a parsed model """

import pytest
from pathlib import Path
from xsm_parser import state_table
from xsm_parser.state_model_parser import StateModelParser

state_machines = [
    "asl",
    "cabin",
    "R53",
    "transfer",
    "door",
    "floor-service",
]


def parse(sm):
    return StateModelParser.parse_file(file_input=Path(__file__).parent / f"state_machines/{sm}.xsm",
                                       debug=False)


@pytest.mark.parametrize("sm", state_machines)
def test_every_model_renders(sm):
    """Each model produces a page headed by its name with a row per wait state"""
    result = parse(sm)
    text = state_table.page(result, f"{sm}.xsm")
    assert text.startswith(f"# {state_table.model_name(result)}")
    assert f"<!-- generated from {sm}.xsm - do not edit -->" in text
    for s in state_table.wait_states(result):
        assert f"| **{s.state.name}** |" in text


def test_creation_event_is_not_a_column():
    """A creation event is answered by the initial transition, not by any state"""
    result = parse("transfer")
    assert "initial" not in state_table.matrix_events(result)


def test_completion_only_columns_are_dropped():
    """An event no wait state answers would be a blank column, so it is omitted"""
    result = parse("cabin")
    assert "Location updated" in state_table.dead_columns(result)
    header = next(l for l in state_table.page(result, "cabin.xsm").splitlines() if l.startswith("| |"))
    assert "Location updated" not in header
    assert "Passing floor" in header  # An interaction event a wait state does answer


# WAITING says nothing about Depart, which can arrive there, and nothing about Done, which cannot
UNDECIDED_MODEL = """domain Test Domain
class Thing
interaction events
    Arrive
    Depart
completion events
    Done
--
state WAITING
activity
transitions
    Arrive > Working
--
state Working
activity
    Done -> me
transitions
    Done > WAITING
--
"""


def test_undecided_responses_are_reported(tmp_path):
    """
    A wait state that declares nothing for an interaction event leaves an open question,
    while the same silence about a completion event is systematic and goes unreported.
    """
    source = tmp_path / "thing.xsm"
    source.write_text(UNDECIDED_MODEL, encoding="utf-8")
    result = StateModelParser.parse_file(file_input=source, debug=False)
    assert state_table.undecided_responses(result) == [("WAITING", "Depart")]
    text = state_table.page(result, "thing.xsm")
    assert "| **WAITING** | **Working** | ? |" in text
    assert "⚠️ 1 interaction event response has not been decided" in text


@pytest.mark.parametrize("sm", state_machines)
def test_every_shipped_model_is_fully_decided(sm):
    """Every response in the elevator models has been considered and written down"""
    assert state_table.undecided_responses(parse(sm)) == []


def test_tag_reference_resolves_to_its_definition():
    """A response citing a tag renders the text supplied where the tag was defined"""
    door = parse("door")
    tags = state_table.tag_table(door)
    reference = next(r for s in door.states for r in s.cant_happens
                     if r.tag == "Cabin not moving" and not r.explanation)
    assert state_table.reason(reference, tags) == tags["Cabin not moving"]


def test_every_event_is_answered_somewhere():
    """No model declares an event that no state responds to"""
    for sm in state_machines:
        assert state_table.orphan_events(parse(sm)) == []


def test_write_defaults_to_the_model_directory(tmp_path):
    """With no output directory the page lands beside the model file"""
    source = tmp_path / "door.xsm"
    source.write_bytes((Path(__file__).parent / "state_machines/door.xsm").read_bytes())
    result = StateModelParser.parse_file(file_input=source, debug=False)
    target = state_table.write(result, source)
    assert target == tmp_path / "door.md"
    assert target.read_text(encoding="utf-8").startswith("# Door")


def test_write_honors_an_output_directory(tmp_path):
    """An output directory is created if it does not already exist"""
    result = parse("door")
    target = state_table.write(result, Path("door.xsm"), tmp_path / "tables")
    assert target == tmp_path / "tables" / "door.md"
    assert target.exists()
