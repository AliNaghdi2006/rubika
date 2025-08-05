
class RubikaAPIError(Exception):
    """
    Exception raised for errors returned by Rubika API.

    Attributes:
        message (str): Explanation of error.
    """

    def __init__(self, message: str = 'An error occurred with Rubika API'):
        self.message = message
        super().__init__(self.message)

class RubikaConnectionError(Exception):
    """
    Exception raised for connection related issues.

    Attributes:
        message (str): Explanation of error.
    """

    def __init__(self, message: str = 'A connection error occurred'):
        self.message = message
        super().__init__(self.message)