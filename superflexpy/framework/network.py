"""
Copyright 2019 Marco Dal Molin et al.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This file is part of the SuperflexPy modelling framework. For details about it,
visit the page https://superflexpy.readthedocs.io

CODED BY: Marco Dal Molin
DESIGNED BY: Marco Dal Molin, Fabrizio Fenicia

This file contains the implementation of the Network class.
"""

from ..utils.generic_component import GenericComponent


class Network(GenericComponent):
    """
    This class defines a Network. A network is a collection of Nodes and it is
    used to route the fluxes from upstream to downstream. A network must be a
    tree.
    """

    def __init__(self, nodes, topography):
        """
        This is the initializer of the class Network.

        Parameters
        ----------
        nodes : list(superflexpy.framework.node.Node)
            List of nodes that belongs to the network. The order is not
            important.
        topography : dict(str : str)
            Topography of the network. Keys are the id of the nodes and values
            are the id of the downstream node the key. Since the network must
            be a tree, each key has only one downstream element
        """

        self._content = nodes
        self._downstream = topography

        self._error_message = 'module : superflexPy, Network ,'
        self._error_message += ' Error message : '

        self._build_network()

    # METHODS FOR THE USER

    def get_output(self, solve=True):
        """
        This method solves the network, solving each node and putting together
        their outputs according to the topography of the network.

        Parameters
        ----------
        solve : bool
            True if the elements have to be solved (i.e. calculate the states).

        Returns
        -------
        :dict(str : list(numpy.ndarray))
            Dictionary containig the output fluxes of all the nodes.
        """

        # Keep track of the solved catchemts
        solved = {k: False for k in self._upstream.keys()}
        output = {}

        # Solve first the headwater
        for cat in self._headwater:
            output[cat] = self._content[self._content_pointer[cat]].get_output(solve)
            solved[cat] = True

        if len(self._content) != len(self._headwater):
            completed = False
        else:
            completed = True

        while not completed:
            for cat in self._upstream.keys():
                if not solved[cat]:
                    # Check if all the upstrams have been solves
                    solvable = True
                    for cat_up in self._upstream[cat]:
                        if not solved[cat_up]:
                            solvable = False
                    if solvable:
                        # Solve the current cathcment
                        loc_out = self._content[self._content_pointer[cat]].get_output(solve)

                        # Multiply for the area
                        for i in range(len(loc_out)):
                            loc_out[i] *= self._content[self._content_pointer[cat]].area

                        for cat_up in self._upstream[cat]:
                            routed_out = self._content[self._content_pointer[cat_up]].external_routing(output[cat_up])
                            if len(loc_out) != len(routed_out):
                                message = '{}Upstream and downstream catchment have '.format(self._error_message)
                                message += 'different number of fluxed. '
                                message += 'Upstream: {}, Local: {}'.format(len(routed_out), len(loc_out))
                                raise RuntimeError(message)
                            for i in range(len(loc_out)):
                                loc_out[i] += routed_out[i] * self._total_area[cat_up]

                        for i in range(len(loc_out)):
                            loc_out[i] /= self._total_area[cat]

                        output[cat] = loc_out
                        solved[cat] = True

                        if self._downstream[cat] is None:
                            completed = True

        return output

    def get_internal(self, id, attribute):
        """
        This method allows to inspect attributes of the objects that belong to
        the network.

        Parameters
        ----------
        id : str
            Id of the object. If it is not a node, it must contain the ids of
            the object containing it. If, for example it is a unit, the id will
            be idNode_idUnit.
        attribute : str
            Name of the attribute to expose.
        Returns
        -------
        Unknown
            Attribute exposed
        """

        cat_num, ele = self._find_attribute_from_name(id)

        if ele:
            return self._content[cat_num].get_internal(id, attribute)
        else:
            try:
                method = getattr(self._content[cat_num], attribute)
                return method
            except AttributeError:
                message = '{}the attribute {} does not exist.'.format(self._error_message, attribute)
                raise AttributeError(message)

    def call_internal(self, id, method, **kwargs):
        """
        This method allows to call methods of the objects that belong to the
        the network.

        Parameters
        ----------
        id : str
            Id of the object. If it is not a node, it must contain the ids of
            the object containing it. If, for example it is a unit, the id will
            be idNode_idUnit.
        method : str
            Name of the method to call.

        Returns
        -------
        Unknown
            Output of the called method.
        """

        cat_num, ele = self._find_attribute_from_name(id)

        if ele:
            return self._content[cat_num].call_internal(id, method, **kwargs)
        else:
            try:
                method = getattr(self._content[cat_num], method)
                return method(**kwargs)
            except AttributeError:
                message = '{}the method {} does not exist.'.format(self._error_message, method)
                raise AttributeError(message)

    # PROTECTED METHODS

    def _build_network(self):
        """
        This method constructs all the structures needed to solve the network
        """

        # Find the upstream catchments
        self._upstream = {k: [] for k in self._downstream.keys()}
        for cat in self._downstream.keys():
            if self._downstream[cat] is not None:
                self._upstream[self._downstream[cat]].append(cat)

        for cat in self._upstream.keys():
            if len(self._upstream[cat]) == 0:
                self._upstream[cat] = None

        # Find the headwater
        self._headwater = [k for k in self._upstream.keys() if self._upstream[k] is None]

        # Build the map from id to index
        self._content_pointer = {cat.id: i for i, cat in enumerate(self._content)}

        # Calculate the total area
        self._total_area = {}
        solved = {k: False for k in self._upstream.keys()}

        # First the headwaters
        for cat in self._headwater:
            self._total_area[cat] = self._content[self._content_pointer[cat]].area
            solved[cat] = True

        if len(self._content) != len(self._headwater):
            completed = False
        else:
            completed = True

        while not completed:
            for cat in self._upstream.keys():
                if not solved[cat]:
                    # Check if all the upstrams have been solves
                    solvable = True
                    for cat_up in self._upstream[cat]:
                        if not solved[cat_up]:
                            solvable = False
                    if solvable:
                        # Solve the current cathcment
                        area = self._content[self._content_pointer[cat]].area

                        for cat_up in self._upstream[cat]:
                            area += self._total_area[cat_up]

                        self._total_area[cat] = area
                        solved[cat] = True

                        if self._downstream[cat] is None:
                            completed = True

    def _find_attribute_from_name(self, id):
        """
        This method is used to find the attributes or methods of the components
        contained for post-run inspection.

        Parameters
        ----------
        id : str
            Identifier of the component

        Returns
        -------
        int, bool
            Index of the component to look for and indication if it is an
            element or a unit (True) or not.
        """

        splitted = id.split('_')

        cat_num = self._find_content_from_name(id)

        if len(splitted) >= 2:
            return (cat_num, True)  # We are looking for a HRU or an element
        else:
            return (cat_num, False)

    # MAGIC METHODS

    def __copy__(self):
        message = '{}A Network cannot be copied'.format(self._error_message)
        raise AttributeError(message)

    def __deepcopy__(self, memo):
        message = '{}A Network cannot be copied'.format(self._error_message)
        raise AttributeError(message)

    def __repr__(self):
        str = 'Module: superflexPy\nNetwork class\n'
        str += 'Nodes:\n'
        str += '\t{}\n'.format(list(self._content_pointer.keys()))
        str += 'Network:\n'
        str += '\t{}\n'.format(self._downstream)

        for cat in self._content:
            str += '********************\n'
            str += '********************\n'
            str += '********************\n'
            str += cat.__repr__()
            str += '\n'
            str += '\n'

        return str