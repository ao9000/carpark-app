
class APIUnavailableError(Exception):
    def __init__(self, api_name, error_code):
        super().__init__(f"API {api_name} returned a status code {error_code}")
