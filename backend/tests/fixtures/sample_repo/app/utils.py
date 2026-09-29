def my_decorator(f):
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapper

@my_decorator
def helper():
    def nested():
        pass
    nested()
    l = lambda x: x
    return l(1)

class Base:
    def method(self):
        pass
        
class Derived(Base):
    def method(self):
        super().method()
