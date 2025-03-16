""" text_elevator_cd_pdf.py - test Starr and xUML notation Elevator class diagram pdf output"""

import pytest
from pathlib import Path
from xsm_parser.state_model_parser import StateModelParser

state_machines = [
    "asl",
    "cabin",
    "R53",
    "transfer",
]

@pytest.mark.parametrize("sm", state_machines)
def test_state_machines(sm):

    input_path = Path(__file__).parent / f"state_machines/{sm}.xsm"
    result = StateModelParser.parse_file(file_input=input_path, debug=False)
    assert result
