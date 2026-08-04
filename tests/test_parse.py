""" text_elevator_cd_pdf.py - test Starr and xUML notation Elevator class diagram pdf output"""

import pytest
from pathlib import Path
from xsm_parser.state_model_parser import StateModelParser

state_machines = [
    "asl",
    "cabin",
    "R53",
    "transfer",
    "door",
    "floor-service",
]

@pytest.mark.parametrize("sm", state_machines)
def test_state_machines(sm):

    input_path = Path(__file__).parent / f"state_machines/{sm}.xsm"
    result = StateModelParser.parse_file(file_input=input_path, debug=False)
    assert result


def parse(sm):
    return StateModelParser.parse_file(file_input=Path(__file__).parent / f"state_machines/{sm}.xsm", debug=False)


def state(result, name):
    return next(s for s in result.states if s.state.name == name)


def test_events_split_by_how_they_arrive():
    """Both event sections are parsed and kept apart"""
    result = parse("door")
    assert result.interaction_events == ["Door opened", "Passenger open", "Passenger close",
                                         "Time to close", "Hold released", "Door closed",
                                         "Lock", "Unlock", "Door blocked"]
    assert result.completion_events == ["Open delay canceled", "Keep trying", "Cannot close door"]


def test_events_field_is_the_union():
    """The events field still holds every declared event, interaction events first"""
    result = parse("door")
    assert result.events == result.interaction_events + result.completion_events
    assert len(result.events) == 12


def test_event_used_for_completion_and_interaction_is_an_interaction_event():
    """
    HOLDING OPEN generates Hold released itself, but the event can also arrive from outside
    when the hold is held, so it is declared as an interaction event rather than a completion
    event. Classification follows the broader use.
    """
    result = parse("door")
    assert "Hold released" in result.interaction_events
    assert "Hold released" not in result.completion_events
    holding_open = state(result, "HOLDING OPEN")
    assert [t.to_state for t in holding_open.transitions if t.event == "Hold released"] == ["CLOSING"]


def test_ignore_and_cant_happen_sections():
    """Both non transition response sections are parsed and kept apart"""
    opening = state(parse("door"), "OPENING")
    assert [r.event for r in opening.ignores] == ["Passenger open", "Lock", "Hold released"]
    assert [r.event for r in opening.cant_happens] == ["Door closed", "Door blocked", "Unlock", "Time to close"]


def test_untagged_explanation():
    """An explanation with no tag keeps its text and its wrapped lines are joined"""
    opening = state(parse("door"), "OPENING")
    passenger_open = opening.ignores[0]
    assert passenger_open.tag is None
    assert passenger_open.explanation.startswith("The passenger can hit the open button")
    assert passenger_open.explanation.endswith("the door is, in fact, opening now.")


def test_tag_definition_carries_explanation():
    """A tag defined at first use supplies both the tag and the explanatory text"""
    unlock = state(parse("door"), "OPENING").cant_happens[2]
    assert unlock.event == "Unlock"
    assert unlock.tag == "Cabin not moving"
    assert unlock.explanation.startswith("Cabin is not able to progress")


def test_inline_tag_reference():
    """A reference may ride on the event line, since it carries no text of its own"""
    completed = state(parse("floor-service"), "COMPLETED")
    assert [(r.event, r.tag, r.explanation) for r in completed.cant_happens] == [
        ("Cabin arrived", "Transfer synch", ""),
        ("Cancel", "Transfer synch", ""),
    ]


def test_tag_reference_has_no_explanation():
    """A reference names the tag only, leaving the explanation to the defining state"""
    unlock = next(r for r in state(parse("door"), "OPEN").cant_happens if r.event == "Unlock")
    assert unlock.tag == "Cabin not moving"
    assert unlock.explanation == ""


def test_every_tag_reference_resolves():
    """No response refers to a tag that is never defined, and no tag is defined twice"""
    result = parse("door")
    responses = [r for s in result.states for r in s.ignores + s.cant_happens if r.tag]
    definitions = [r.tag for r in responses if r.explanation]
    assert len(definitions) == len(set(definitions))
    assert {r.tag for r in responses} == set(definitions)


def test_state_without_response_sections():
    """A state may still omit both sections entirely"""
    cancel = state(parse("door"), "Cancel open delay")
    assert cancel.ignores == []
    assert cancel.cant_happens == []
    assert [t.event for t in cancel.transitions] == ["Open delay canceled"]


def test_cant_happen_without_transitions():
    """A final state has no transitions section but may still declare can't happen responses"""
    cannot_close = state(parse("door"), "CANNOT CLOSE")
    assert cannot_close.transitions == []
    assert len(cannot_close.cant_happens) == 8
