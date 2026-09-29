from ..db import connect

def validate_user():
    pass

class UserService:
    def __init__(self):
        self.db = connect()
    def get(self):
        pass
    def create(self, data):
        validate_user()
        return True
    def delete(self):
        pass
