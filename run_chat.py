###############################################################################
#
# Copyright 2019, University of Stuttgart: Institute for Natural Language Processing (IMS)
#
# This file is part of Adviser.
# Adviser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3.
#
# Adviser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adviser.  If not, see <https://www.gnu.org/licenses/>.
#
###############################################################################

"""
This module allows to chat with the dialog system.

NOTE: this is not intended as an integration test!
"""

from utils import common
import os
import argparse
from utils.logger import DiasysLogger, LogLevel

from utils.common import Language
from dialogsystem import DialogSystem
from modules.nlu import HandcraftedNLU
from modules.bst import HandcraftedBST
from modules.nlg import HandcraftedNLG
from modules.policy.policy_handcrafted import HandcraftedPolicy
from modules.policy.policy_handcrafted_student import HandcraftedStudentPolicy
from modules.surfaces import ConsoleInput, ConsoleOutput
from utils.domain.jsonlookupdomain import JSONLookupDomain


def start_dialog(domain_name: str, logger: DiasysLogger, default_policy: bool):
    """ Start chat with system.

    Args:
        domain_name (str): name of domain (according to the names in resources/databases)
        logger (DiasysLogger): logger for all modules
    """

    # init domain
    domain = JSONLookupDomain(name=domain_name)

    # init modules
    input_module = ConsoleInput(domain, logger=logger)
    nlu = HandcraftedNLU(domain=domain, logger=logger)
    bst = HandcraftedBST(domain=domain, logger=logger)
    if default_policy:
        policy = HandcraftedPolicy(domain=domain, logger=logger)
    else:
        policy = HandcraftedStudentPolicy(domain=domain, logger=logger)
    nlg = HandcraftedNLG(domain=domain, logger=logger)
    output_module = ConsoleOutput(domain, logger=logger)

    # construct dialog graph
    ds = DialogSystem(
        input_module,
        nlu,
        policy,
        nlg,
        bst,
        output_module,
        logger=logger)

    # start chat
    ds.run_dialog()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--domain", required=False, choices=['IMSCourses', 'superhero'],
                        help="single domain choice: IMSCourses |superhero",
                        default='superhero')
    parser.add_argument("-lf", "--logtofile", action="store_true", help="log dialog to filesystem")
    parser.add_argument("-dp", "--default_policy", action="store_true", help="use default policy implementation")
    args = parser.parse_args()

    # init logger
    file_log_lvl = LogLevel.DIALOGS if args.logtofile else LogLevel.NONE
    logger = DiasysLogger(console_log_lvl=LogLevel.NONE, file_log_lvl=file_log_lvl)

   
    start_dialog(domain_name=args.domain, logger=logger, default_policy=args.default_policy)
