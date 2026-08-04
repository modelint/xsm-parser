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

def get_logger():
    """Initiate the logger"""
    log_conf_path = Path(__file__).parent / 'log.conf'  # Logging configuration is in this file
    logging.config.fileConfig(fname=log_conf_path, disable_existing_loggers=False)
    return logging.getLogger(__name__)  # Create a logger for this module

# Configure the expected parameters and actions for the argparse module
def parse(cl_input):
    """
    The command line interface is for diagnostic purposes

    :param cl_input:
    :return:
    """
    parser = argparse.ArgumentParser(description=_progname)
    parser.add_argument('smfile', nargs='?', action='store',
                        help='State model file name with .xsm extension')
    parser.add_argument('-t', '--table', action='store_true',
                        help='Generate a markdown state transition table for the model')
    parser.add_argument('-o', '--output', action='store',
                        help='Directory to write the table into, defaults to the model file directory')
    parser.add_argument('-D', '--debug', action='store_true',
                        help='Debug mode'),
    parser.add_argument('-V', '--version', action='store_true',
                        help='Print the current version of parser')
    return parser.parse_args(cl_input)


def main():
    # Start logging
    logger = get_logger()
    logger.info(f'{_progname} version: {version}')

    # Parse the command line args
    args = parse(sys.argv[1:])

    if args.version:
        # Just print the version and quit
        print(f'{_progname} version: {version}')
        sys.exit(0)

    if args.table and not args.smfile:
        sys.exit("A state model file is required to generate a table")

    if args.smfile:
        fpath = Path(args.smfile)
        d = args.debug
        result = StateModelParser.parse_file(file_input=fpath, debug=d)

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
    print("\nNo problemo")


if __name__ == "__main__":
    main()
