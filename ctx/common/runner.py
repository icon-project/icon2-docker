import asyncio


class AsyncRunner:
    def __init__(self, command_list=None):
        if isinstance(command_list, list):
            self.command_list = command_list
        else:
            self.command_list = []

    def run(self):
        asyncio.run(self.run_managers())

    def push(self, command=None):
        if command:
            self.command_list.append(command)

    async def run_managers(self):
        if isinstance(self.command_list, list):
            await asyncio.wait(self.command_list)
