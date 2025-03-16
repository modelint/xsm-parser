""" state_model_visitor.py """

from arpeggio import PTNodeVisitor
from collections import namedtuple

# These named tuples help package up parsed data into meaningful chunks of state model content
# To avoid a collision with any application tuple names, we append _p to indicate parser output
StateBlock_a = namedtuple('StateBlock_a', 'state activity transitions')
"""Parsed model data describing a state including its activity, optional creation event and optional exit transitions"""
Parameter_a = namedtuple('Parameter_a', 'name type')
"""Parsed name and data type of a parameter in a state model event signature"""
StateSpec_a = namedtuple('StateSpec_a', 'name deletion signature')
"""Parsed name of a real state, its type (deletion or non deletion) and state signature"""
Transition_a = namedtuple('Transition_a', 'event to_state')
"""Parsed transition with event and destination state"""

StateModel_a = namedtuple('State_model_a', 'metadata domain lifecycle assigner_rnum assigner_pclass '
                                           'initial_transitions events states')
"""A complete statemodel result"""

class StateModelVisitor(PTNodeVisitor):
    """Visit parsed units of an Executable UML State Model"""
    # Each header comment below corresponds to section in state_model.peg file

    # Root
    @classmethod
    def visit_statemodel(cls, node, children):
        """ EOL* metadata? domain_header (lifecycle / assigner) events* initial_transitions* state_block* EOF """

        metadata = children.results.get('metadata', None)  # Optional section
        domain = children.results.get('domain_header')[0]
        lifecycle = children.results.get('lifecycle')
        lifecycle_class = None if not lifecycle else lifecycle[0]['class']
        assigner = children.results.get('assigner')
        assigner_rnum = None if not assigner else assigner[0]['rel']
        assigner_pclass = None if not assigner else assigner[0].get('pclass')
        events = children.results.get('events', [])
        states = children.results.get('state_block')
        itrans = children.results.get('initial_transitions', [])

        return StateModel_a(
            domain=domain,
            lifecycle=lifecycle_class,
            assigner_rnum=assigner_rnum,
            assigner_pclass=assigner_pclass,
            events=events if not events else events[0],
            states=states,
            initial_transitions=itrans if not itrans else itrans[0],
            metadata=None if not metadata else metadata[0]
        )

    # Metadata
    @classmethod
    def visit_metadata(cls, node, children):
        """ metadata_header data_item* """
        items = {k: v for c in children for k, v in c.items()}
        return items

    @classmethod
    def visit_data_item(cls, node, children):
        """ INDENT name SP* (resource_item / text_item) EOL* """
        return { children[0]: children[1] }

    @classmethod
    def visit_resource_item(cls, node, children):
        """ '>' SP* name """
        return ''.join(children), True  # Item, Is a resource

    @classmethod
    def visit_text_item(cls, node, children):
        """ ':' SP* r'.*' """
        return children[0], False  # Item, Not a resource

    # Scope headers
    @classmethod
    def visit_domain_header(cls, node, children):
        """ "domain" SP name EOL* """
        name = children[0]
        return name

    @classmethod
    def visit_lifecycle(cls, node, children):
        """ "class" SP name EOL* """
        return {'class': children[0] }

    @classmethod
    def visit_assigner(cls, node, children):
        """ "relationship" SP rnum SP '/' SP name? EOL* """
        item = {'rel': children[0] }
        if len(children) == 2:
            item['pclass'] = children[1]
        return item

    # Events
    @classmethod
    def visit_events(cls, node, children):
        """A list of event names"""
        return list(children)

    @classmethod
    def visit_event_spec(cls, node, children):
        """ INDENT event_name EOL* """
        return children[0]

    @classmethod
    def visit_event_name(cls, node, children):
        """ name """
        name = ''.join(children)
        return name

    # Initial transitions
    @classmethod
    def visit_initial_transitions(cls, node, children):
        """ it_header transition* block_end """
        return children

    # State block
    @classmethod
    def visit_state_block(cls, node, children):
        """ state_header activity transitions? block_end """
        s = children[0]  # State info
        a = children[1]  # Activity (could be empty, but always provided)
        t = [] if len(children) < 3 else children[2]  # Optional transitions
        sblock = StateBlock_a(state=s, activity=a, transitions=t)
        return sblock

    @classmethod
    def visit_state_header(cls, node, children):
        """
        "state" sp state_name signature? (sp deletion)? EOL*

        There are four possible cases:
            state name
            state name (deletion)
            state name (signature)
            state name (signature) (deletion)
        """
        n = children[0]  # State name
        clen = len(children)
        deletion = True if clen > 1 and 'deletion' in children else False
        sig = []
        if deletion and clen == 3 or not deletion and clen == 2:
            sig = children[1]
        return StateSpec_a(name=n, deletion=deletion, signature=sig)

    @classmethod
    def visit_signature(cls, node, children):
        """ '()' / '(' SP? parameter_set SP? ')' """
        return children[0]

    @classmethod
    def visit_parameter_set(cls, node, children):
        """ parameter (',' SP parameter)* """
        return children

    @classmethod
    def visit_parameter(cls, node, children):
        """ parameter_name SP? ':' SP? type_name """
        return Parameter_a(name=children[0], type=children[1])

    @classmethod
    def visit_parameter_name(cls, node, children):
        """ name """
        name = ''.join(children)
        return name

    @classmethod
    def visit_type_name(cls, node, children):
        """ name """
        name = ''.join(children)
        return name

    @classmethod
    def visit_DELETION(cls, node, children):
        """ r'!*' """
        return 'deletion'

    @classmethod
    def visit_activity(cls, node, children):
        """ activity_header body_line* """
        return children

    @classmethod
    def visit_transitions(cls, node, children):
        """ transition_header transition* """
        return children

    @classmethod
    def visit_transition(cls, node, children):
        """ INDENT event_name (SP '>' SP state_name)? EOL* """
        return Transition_a(event=children[0], to_state=None if len(children) < 2 else children[1])

    @classmethod
    def visit_state_name(cls, node, children):
        """ name """
        name = ''.join(children)
        return name

    # Elements
    @classmethod
    def visit_body_line(cls, node, children):
        """ INDENT r'.*\n' """
        body_text_line = children[0]
        return body_text_line

    @classmethod
    def visit_name(cls, node, children):
        """ word (delim word)* """
        name = ''.join(children)
        return name

    # Discarded whitespace and comments
    @classmethod
    def visit_LINEWRAP(cls, node, children):
        """
        EOL SP*
        end of line followed by optional INDENT on next line
        """
        return None

    @classmethod
    def visit_EOL(cls, node, children):
        """
        SP* COMMENT? '\n'

        end of line: Spaces, Comments, blank lines, whitespace we can omit from the parser result
        """
        return None

    @classmethod
    def visit_SP(cls, node, children):
        """ ' '  Single space character (SP) """
        return None
