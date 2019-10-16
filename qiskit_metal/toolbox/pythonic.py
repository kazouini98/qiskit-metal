'''
Utility functions that are mostly pythonic

@date: 2019
@author: Zlatko K. Minev
'''
import traceback
import warnings

import pandas as pd
from copy import deepcopy


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """
    import functools
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter('always', DeprecationWarning)  # turn off filter
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                      category=DeprecationWarning,
                      stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning)  # reset filter
        return func(*args, **kwargs)
    return new_func

####################################################################################
### Dictionary related

def copy_update(options, *args, deep_copy = True, **kwargs):
    '''
    Utility funciton to merge two dictionaries
    '''
    if deep_copy:
        options = deepcopy(options)
        options.update(*args, **kwargs)
    else:
        options = options.copy()
        options.update(*args, **kwargs)
    return options

def dict_start_with(my_dict, start_with, as_=list):
    ''' Case sensise
                    https://stackoverflow.com/questions/17106819/accessing-python-dict-values-with-the-key-start-characters
    my_dict = {'name': 'Klauss', 'age': 26, 'Date of birth': '15th july'}
    dict_start_with(my_dict, 'Date')
    '''
    if as_ == list:
        return [v for k, v in my_dict.items() if k.startswith(start_with)] #start_with in k]
    elif as_ == dict:
        return {k:v for k, v in my_dict.items() if k.startswith(start_with)}


def display_options(*ops_names, options = None, find_dot_keys=True, do_display=True):
    '''
    Print html display of options dictionary by default `DEFAULT_OPTIONS`

    Example use:
    ---------------
        display_options('make_transmon_pocket_v1', 'make_transmon_connector_v1')

    or
        dfs, html = display_options(Metal_Transmon_Pocket.__name__, do_display=False)
    '''
    #IDEA: display also ._hfss and ._gds etc. for those that lhave it and add to plugins
    if options is None:
        from ..draw_functions import DEFAULT_OPTIONS
        options = DEFAULT_OPTIONS

    res = []
    for keyname in ops_names:
        if find_dot_keys:
            names = list(filter(lambda x, match=keyname: x is match or\
                             x.startswith(match+'.'), DEFAULT_OPTIONS.keys()))
            names.sort()
            for name in names:
                res += [pd.Series(options[name], name=name).to_frame()]
        else:
            res += [pd.Series(options[keyname], name=keyname).to_frame()]

    from pyEPR.toolbox import display_dfs
    res_html = display_dfs(*res, do_display=do_display)
    return res, res_html

####################################################################################
### Tracebacks

_old_warn = None
def enable_warning_traceback():
    """Show ow traceback on warning
    """

    global _old_warn
    _old_warn = warnings.warn
    def warn(*args, **kwargs):
        '''
        Warn user with traceback to warning
        '''
        tb = traceback.extract_stack()
        _old_warn(*args, **kwargs)
        print("".join(traceback.format_list(tb)[:-1]))
    warnings.warn = warn

def get_traceback():
    '''
    Returns tracekback string
    '''
    tb = traceback.extract_stack()
    return "".join(traceback.format_list(tb)[:-1])


def print_traceback_easy(start=26):
    '''
    Utility funciton to print traceback for debug
    '''
    print(f"\n")
    print('\n'.join(map(repr,traceback.extract_stack()[start:])))
    print('\n')

####################################################################################
### ...