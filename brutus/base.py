# -*- coding: utf-8 -*-

import abc


class BrutusBackend:
    """
    Base class for all compute backends.
    """

    @abc.abstractmethod
    def dispatch(self, func: callable, *args, **kwargs):
        """
        Method which sends function and arguments off to get computed
        and waits for the response

        typically call self.func(*args, **kwargs) remotely
        """
        ...

