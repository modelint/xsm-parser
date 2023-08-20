""" state_model_parser.py – First attempt to parse class block """

from xsm_parser.exceptions import ModelGrammarFileOpen, ModelInputFileOpen, ModelInputFileEmpty, ModelParseError
from xsm_parser.state_model_visitor import StateModelVisitor, StateModel_a
from arpeggio import visit_parse_tree, NoMatch
from arpeggio.cleanpeg import ParserPEG
import os
from pathlib import Path


class StateModelParser:
    """
    Parses an Executable UML state model input file using the arpeggio parser generator

        Attributes

        - grammar_file -- (class based) Name of the system file defining the Executable UML grammar
        - root_rule_name -- (class based) Name of the top level grammar element found in grammar file
        - debug -- debug flag (used to set arpeggio parser mode)
        - model_grammar -- The model grammar text read from the system grammar file
        - model_text -- The input model text read from the user supplied text file
    """
    debug = False  # by default
    xsm_grammar = None  # We haven't read it in yet
    model_text = None  # User will provide this in a file
    model_file = None  # The user supplied xsm file path

    root_rule_name = 'statemodel'  # The required name of the highest level parse element

    # Useful paths within the project
    src_path = Path(__file__).parent.parent  # Path to src folder
    module_path = src_path / 'xsm_parser'
    grammar_path = module_path  # The grammar files are all here
    cwd = Path.cwd()
    diagnostics_path = cwd / 'diagnostics'  # All parser diagnostic output goes here

    # Files
    grammar_file = grammar_path / "state_model.peg"  # We parse using this peg grammar
    grammar_model_pdf = diagnostics_path / "state_model.pdf"
    parse_tree_pdf = diagnostics_path / "state_parse_tree.pdf"
    parse_tree_dot = cwd / f"{root_rule_name}_parse_tree.dot"
    parser_model_dot = cwd / f"{root_rule_name}_peg_parser_model.dot"

    pg_tree_dot = cwd / "peggrammar_parse_tree.dot"
    pg_model_dot = cwd / "peggrammar_parser_model.dot"
    pg_tree_pdf = diagnostics_path / "peggrammar_parse_tree.pdf"
    pg_model_pdf = diagnostics_path / "peggrammar_parser_model.pdf"

    @classmethod
    def parse_file(cls, file_input: Path, debug=False):
        """

        :param file_input:  class model file to read
        :param debug:  Run parser in debug mode
        """
        cls.model_file = file_input
        cls.debug = debug
        if debug:
            # If there is no diagnostics directory, create one in the current working directory
            cls.diagnostics_path.mkdir(parents=False, exist_ok=True)

        # Read the state model file
        try:
            cls.model_text = open(file_input, 'r').read() + '\n'
            # At least one newline at end simplifies grammar rules
        except OSError as e:
            raise ModelInputFileOpen(file_input)

        if not cls.model_text:
            raise ModelInputFileEmpty(file_input)

        return cls.parse()

    @classmethod
    def parse(cls) -> StateModel_a:
        """
        Parse the model file and return the content
        :return:  The abstract syntax tree content of interest
        """
        # Read the grammar file
        try:
            cls.xsm_grammar = open(cls.grammar_file, 'r').read()
        except OSError as e:
            raise ModelGrammarFileOpen(cls.grammar_file)

        # Create an arpeggio parser for our model grammar that does not eliminate whitespace
        # We interpret newlines and indents in our grammar, so whitespace must be preserved
        parser = ParserPEG(cls.xsm_grammar, StateModelParser.root_rule_name, skipws=False, debug=cls.debug)
        if cls.debug:
            # Transform dot files into pdfs
            # os.system(f'dot -Tpdf {cls.pg_tree_dot} -o {cls.pg_tree_pdf}')
            # os.system(f'dot -Tpdf {cls.pg_model_dot} -o {cls.pg_model_pdf}')
            os.system(f'dot -Tpdf {cls.parser_model_dot} -o {cls.grammar_model_pdf}')
            cls.parser_model_dot.unlink(True)
            cls.pg_tree_dot.unlink(True)
            cls.pg_model_dot.unlink(True)

        # Now create an abstract syntax tree from our model text
        try:
            parse_tree = parser.parse(cls.model_text)
        except NoMatch as e:
            raise ModelParseError(cls.model_file.name, e) from None

        # Transform that into a result that is better organized with grammar artifacts filtered out
        result = visit_parse_tree(parse_tree, StateModelVisitor(debug=cls.debug))

        if cls.debug:
            # Transform dot files into pdfs
            os.system(f'dot -Tpdf {cls.parse_tree_dot} -o {cls.parse_tree_pdf}')
            # Delete dot files since we are only interested in the generated PDFs
            # Comment this part out if you want to retain the dot files
            cls.parse_tree_dot.unlink(True)

        return result
