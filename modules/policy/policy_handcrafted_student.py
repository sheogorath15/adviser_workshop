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

from typing import List

from utils.domain.jsonlookupdomain import JSONLookupDomain
from utils import SysAct, SysActionType
from utils.logger import DiasysLogger
from utils import useract as u
from utils.beliefstate import BeliefState
from policy_handcrafted import HandcraftedPolicy


class HandcraftedStudentPolicy(HandcraftedPolicy):
    """ Base class for handcrafted policies.

    Provides a simple rule-based policy. Can be used for any domain where a user is
    trying to find an entity (eg. a course from a module handbook) from a database
    by providing constraints (eg. semester the course is offered) or where a user is
    trying to find out additional information about a named entity.

    Output is a system action such as:
     * inform -- provides information on an entity
     * request -- request more information from the user
     * bye -- issue parting message and end dialog

    In order to create your own policy, you can inherit from this class.
    Make sure to overwrite the `forward`-method with whatever additionally
    rules/functionality required.

    """
    def __init__(self, domain: JSONLookupDomain, subgraph=None,
                 logger: DiasysLogger = DiasysLogger()):
        """
        Initializes the policy

        Arguments:
            domain {domain.jsonlookupdomain.JSONLookupDomain} -- Domain

        """
        super(HandcraftedPolicy, self).__init__(domain, subgraph=None, logger=logger)
        self.turn = 0
        self.last_action = None
        self.current_suggestions = []  # list of current suggestions
        self.s_index = 0  # the index in current suggestions for the current system reccomendation
        self.domain_key = domain.get_primary_key()
        self.act_types_lst = []

    def forward(self, dialog_graph, beliefstate: BeliefState = None,
                user_acts: List[u.UserAct] = None,  sys_act: SysAct = None,
                **kwargs) -> dict(sys_act=SysAct):

        """
            Responsible for walking the policy through a single turn. Uses the current user
            action and system belief state to determine what the next system action should be.

            To implement an alternate policy, this method may need to be overwritten

            Args:
                dialog_graph (DialogSystem): the graph to which the policy belongs
                beliefstate (BeliefState): a BeliefState obejct representing current system
                                           knowledge
                user_acts (list): a list of UserAct objects mapped from the user's last utterance
                sys_act (SysAct): this should be None

            Returns:
                (dict): a dictionary with the key "sys_act" and the value that of the systems next
                        action

        """
        # variables for general (non-domain specific) actions
        self.turn = dialog_graph.num_turns
        self.prev_sys_act = sys_act

        # removes semantically unimportant actions
        # (eg. Hello/thanks if other actions are also present)
        self._check_for_gen_actions(user_acts)

        # on the first turn, return a Welcome action
        if user_acts is None and self.turn == 0:
            sys_act = SysAct()
            sys_act.type = SysActionType.Welcome
            return sys_act

        ###############################################################################
        # TODO: add reactions to the different general user acts here                 #
        #       consider when you should issue a Bad act? When should the system      #
        #       return a Bye act? If the user says thank you, how should you respond? #
        #       Use the welcome act as a template for creating system acts            #
        ###############################################################################

        elif u.UserActionType.Hello in self.act_types_lst:
            # If user only says hello, request a random slot to move dialog along
            sys_act = SysAct()
            sys_act.type = SysActionType.Request
            sys_act.add_value(self._get_open_slot(beliefstate))

        else:
            # Else handle domain specific actions

            ############################################################################
            # TODO: edit _next(action) to determine what the next system act should be #
            ############################################################################
            sys_act = self._next_action(beliefstate)

        self.logger.dialog_turn("System Action: " + str(sys_act))
        return {'sys_act': sys_act}

    def _next_action(self, beliefstate: BeliefState):
        """Determines the next system action based on the current belief state and
           previous action.

           When implementing a new type of policy, this method MUST be rewritten

        Args:
            beliefstate (HandCraftedBeliefState): system values on liklihood
            of each possible state

        Return:
            (SysAct): the next system action

        --LV
        """

        # figure out what general type of user utterance it is
        # returns a string describing what general type (method) the user action was
        method = self._get_method(beliefstate)

        # Assuming this happens only because domain is not actually active
        if method == 'none':
            ################################################
            # TODO: return new SysAct object with type Bad #
            ################################################
            pass

        # If the user asks for alternatives before any constraints have ben specified, it's bad
        elif method == 'byalternatives' and not self._get_constraints(beliefstate)[0]:
            #################################################
            # TODO: return new SysAct object with type  Bad #
            #################################################
            pass

        # if the user asks for information about an entity before any are mentioned, ask what they
        # want to know about it
        elif method == 'byprimarykey' and not self._get_requested_slots(beliefstate):
            sys_act = SysAct()
            sys_act.type = SysActionType.InformByName
            sys_act.add_value(self.domain.get_primary_key(), self._get_name(beliefstate))
            beliefstate['system']['lastInformedPrimKeyVal'] = self._get_name(beliefstate)
            return sys_act

        # Otherwise we need to query the db to determine next action
        results = self._query_db(beliefstate)

        ##########################################################################
        # TODO: edit _raw_action() to decide if the next system action should be #
        #       an inform or a request                                           #
        ##########################################################################
        sys_act = self._raw_action(results, method, beliefstate)

        # requests are fairly easy, if it's a request, return it directly
        if sys_act.type == SysActionType.Request:
            if len(list(sys_act.slot_values.keys())) > 0:
                # update the belief state to reflec the slot we just asked about
                beliefstate['system']['lastRequestSlot'] = list(sys_act.slot_values.keys())[0]

        # otherwise we need to convert a raw inform into one with proper slots and values
        elif sys_act.type == SysActionType.InformByName:
            self._convert_inform(method, results, sys_act, beliefstate)
            # update belief state to reflect the offer we just made
            values = sys_act.get_values(self.domain.get_primary_key())
            if values:
                beliefstate['system']['lastInformedPrimKeyVal'] = values[0]
            else:
                sys_act.add_value(self.domain.get_primary_key(), 'none')

        return sys_act

    def _raw_action(self, q_res: iter, method: str, beliefstate: BeliefState):
        """Based on the output of the db query and the method, choose
           whether next action should be request or inform

        Args:
            q_res (list): rows (list of dicts) returned by the issued sqlite3
            query
            method (str): the type of user action
                     ('byprimarykey', 'byconstraints', 'byalternatives')

        Returns:
            (SysAct): SysAct object of appropriate type; if a request, with the next slot
                      to request; if an inform, this can be empty for now

        --LV
        """
        ####################################################################################
        # TODO:                                                                            #
        # consider: under what condtions should the next action be a request? Under which  #
        #           conditions should the next action be an inform? Think about the method #
        #           (is it by_name or by_constraints) has an offer already been made? How  #
        #           many database results are there? Could you split them up more? If you  #
        #           asked for more constraints?                                            #
        ####################################################################################
        pass
