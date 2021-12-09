class Lazy(object):
    def __init__(self, fn, *fn_args, **fn_kwargs):
        self.fn = fn
        self.fn_args = fn_args
        self.fn_kwargs = fn_kwargs

        self._value = None
        self._set_value = False

    def __enter__(self): 
        if not self._set_value:
            self._value = self.fn(*self.fn_args, **self.fn_kwargs)
            self._set_value = True
        return self._value
    
    def __exit__(self, *_):
        pass