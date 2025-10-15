
def identify_error(e):
    return isinstance(e, Exception) and str(e).startswith("{")

