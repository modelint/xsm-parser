"""
__main__.py

State Model Parser
"""

import logging
import logging.config
import sys
import argparse
from pathlib import Path
from xsm_parser import version
from xsm_parser import state_table
from xsm_parser.state_model_parser import StateModelParser

_logpath = Path("xsm_parser.log")
_progname = 'State model parser'

def get_logger(to_file: bool):
    """
    Initiate the logger

    The log file is written into the current working directory, so we only open one when the
    user asks for it. Otherwise the logger is left with a null handler and the messages go nowhere.

    :param to_file: Write a log file as configured in log.conf
    :return: A logger for this module
    """
    if to_file:
        log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
        logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    else:
        logging.getLogger().addHandler(logging.NullHandler())
    return logging.getLogger(__name__)  # Create a logger for this module

# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    """
    Define the command line interface

    :param cl_input:
    :return:
    """
    parser = argparse.ArgumentParser(prog='xsm', description=_progname)
    parser.add_argument('smfile', nargs='?', action='store',
                        help='State model file name with .xsm extension')
    parser.add_argument('-t', '--table', action='store_true',
                        help='Generate a markdown state transition table for the model')
    parser.add_argument('-o', '--output', action='store',
                        help='Directory to write the table into, defaults to the model file directory')
    parser.add_argument('-L', '--log', action='store_true',
                        help=f'Generate a diagnostic {_logpath} file in the current directory')
    parser.add_argument('-D', '--debug', action='store_true',
                        help='Debug mode'),
    parser.add_argument('-V', '--version', action='store_true',
                        help='Print the current version of parser')
    return parser, parser.parse_args(cl_input)


def main():
    # Parse the command line args before logging, since one of them decides whether we log at all
    parser, args = parse(sys.argv[1:])

    logger = get_logger(to_file=args.log)
    logger.info(f'{_progname} version: {version}')

    if args.version:
        # Just print the version and quit
        print(f'{_progname} version: {version}')
        sys.exit(0)

    if not args.smfile:
        # Nothing to work on, so show the user what they can ask for
        parser.print_help()
        sys.exit(0 if len(sys.argv) == 1 else 2)

    fpath = Path(args.smfile)
    result = StateModelParser.parse_file(file_input=fpath, debug=args.debug)

    if args.table:
        target = state_table.write(result, fpath, args.output)
        logger.info(f'Wrote state transition table: {target}')
        print(f"Wrote {target}")
        # These don't stop the table from being written, but the modeler should know
        undecided = state_table.undecided_responses(result)
        if undecided:
            print(f"  {len(undecided)} interaction event response(s) not yet decided")
        orphans = state_table.orphan_events(result)
        if orphans:
            print(f"  declared but never answered by any state: {', '.join(orphans)}")

    logger.info("No problemo")  # We didn't die on an exception, basically
    if args.debug:
        print("\nNo problemo")


if __name__ == "__main__":
    main()
