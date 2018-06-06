'''Utilities. This module contains non-essential helper methods.'''

import sys

from django.db.models import Q


def print_q_expr(expr, indent="", is_tail=True): # pragma: no cover
    '''
    Simple print method for debugging Q-expressions' trees.
    '''
    sys.stdout.write(indent)
    sa, sb = (' └── ', '    ') if is_tail else (' ├── ', ' │   ')

    if isinstance(expr, Q):
        sys.stdout.write('{}{}\n'.format(sa, expr.connector))
        for child in expr.children:
            print_q_expr(child, indent + sb, expr.children[-1] == child)
    else:
        try:
            queryset = ', '.join(repr(v) for v in expr[1])
        except TypeError:
            queryset = repr(expr[1])
        sys.stdout.write(' └── {} {}\n'.format(expr[0], queryset))
