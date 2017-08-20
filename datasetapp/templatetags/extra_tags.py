from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@stringfilter
def slice_string(value, args):
    """
    Slices a string: returns characters in string, starting with ``start``
    and ending *one character* before ``end``.

    Examples:
    {{ 'my_long_string' | slice_string:"2" }}  will return '_'
    {{ 'my_long_string' | slice_string:":2" }}  will return 'my'
    {{ 'my_long_string' | slice_string:"0:3" }} will return 'my'
    {{ 'my_long_string' | slice_string:"3:7" }} will return 'long'
    {{ 'my_long_string' | slice_string:"8:" }}    will return 'string'
    {{ 'my_long_string' | slice_string:"8:100" }} will return 'string'
    {{ 'my_long_string' | slice_string:"8:14" }}  will return 'string'
    """
    sep = ':'
    if args is None:
        return False
    if ':' not in args:
        return value[int(args)]

    slicer = [int(arg.strip()) for arg in args.split(sep) if arg != '']
    if args[0] == sep:
        start, end = 0, slicer[0]
    elif args[-1] == sep:
        start, end = slicer[0], len(value)
    else:
        start, end = slicer
    return value[start:end]

# slice_string.is_safe = True: rather leave off; incase use removes part of string
# that causes it to become unsafe.

register.filter('slice_string', slice_string)