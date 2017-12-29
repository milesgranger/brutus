# -*- coding: utf-8 -*-

import abc
from typing import Iterable


class BrutusBackend:
    """
    Base class for all compute backends.
    """

    @abc.abstractmethod
    def submit(self, func: callable, *args, **kwargs):
        """
        Submit one function call
        """
        ...

    @abc.abstractmethod
    def map(self, func: callable, iter: Iterable):
        """
        Map an iterable over a function
        """
        ...