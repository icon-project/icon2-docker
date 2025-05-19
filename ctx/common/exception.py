class SeedConnectionError(Exception):
    def __init__(self, message="Cannot connect to the seed server."):
        self.message = message
        super().__init__(self.message)


class FileSystemException(Exception):
    def __init__(self, message="Unable to complete the file system operation."):
        self.message = message
        super().__init__(self.message)


class ConfigException(Exception):
    def __init__(self, message="The configuration value is invalid."):
        self.message = message
        super().__init__(self.message)
