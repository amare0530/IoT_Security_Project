class VRFError(Exception):
    """
    Base class for exceptions in VRF.py.
    """
    pass

class SeedError(VRFError):
    """
    Exception raised for errors related to the seed generation or revelation.
    """
    def __init__(self, message="Seed error occurred."):
        self.message = message
        super().__init__(self.message)

class VerificationError(VRFError):
    """
    Exception raised for errors during the verification process.
    """
    def __init__(self, message="Verification failed."):
        self.message = message
        super().__init__(self.message)

class InputError(VRFError):
    """
    Exception raised for invalid input parameters.
    """
    def __init__(self, message="Invalid input provided."):
        self.message = message
        super().__init__(self.message)