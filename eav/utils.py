from future import __print_function__

def print_q_expr(expr, i=None):
    '''
    Dirty and fast method to visualise Q-expression tree.
    '''
    i = i or 0
    if type(expr) == models.Q:
        print(i * '    ' + '└── ' + expr.connector)
        for child in expr.children:
            print_q_expr(child, i + 1)
    else:
        try:
            queryset = ', '.join(repr(v) for v in expr[1])
        except TypeError:
            queryset = repr(expr[1])
        print(i * '    ' + '└── ' + expr[0] + ' ' + queryset)
