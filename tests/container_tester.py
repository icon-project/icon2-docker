# -*- coding: utf-8 -*-
import append_parent_path
import os
import sys
import yaml
import unittest
import inspect
import subprocess
import re
import requests
from urllib.request import urlopen
from ctx.common import converter
from termcolor import cprint, colored
from devtools import debug
import time
import timeit
import unittest.runner
import itertools
from pawnlib.output import print_syntax


# class DockerComposeExecutor(object):
#     def __init__(self, compose_files, project_name):
#         self._compose_files = compose_files
#         self._project_name = project_name
#         self.project_directory = os.path.dirname(os.path.realpath(compose_files[0]))
#
#     def execute(self, *subcommand):
#         command = ["docker-compose", "--project-directory", self.project_directory]
#         for compose_file in self._compose_files:
#             command.append('-f')
#             command.append(compose_file)
#         command.append('-p')
#         command.append(self._project_name)
#         command += subcommand
#         return execute(command)


class ContainerTestCase(unittest.TestCase):
    docker_compose_file = "docker-compose.yml"
    container_path = "goloop_container"
    file_path = os.path.dirname(os.path.realpath(__file__))
    docker_compose_path = f"{file_path}/{container_path}"
    compose_service_name = "icon2-node"
    docker_compose_content = {}
    make_args = {}
    # sys.tracebacklimit = 0

    image_name = None
    image_version = None
    service = None
    version = None
    tag_name = None
    seed_domain = None

    is_debug = False
    is_reset_container_path = True
    is_from_compose_template = True
    is_control_container = True

    blockheight_info = {
        "first": 0,
        "last": 0,
    }

    @staticmethod
    def log_point(msg="", color="green"):
        'utility method to trace control flow'
        # calling_file = inspect.stack()[1][1].replace(FILE_PATH, "")
        calling_file = ""
        calling_function = inspect.stack()[1][3]
        if color == "white":
            text = f"{msg} ... "
            end = ""
            flush = True
        else:
            text = f"[{converter.todaydate('time')}][{calling_file}{calling_function}()] {msg}"
            end = None
            flush = True
        cprint(text, color, end=end, flush=flush)

    def execute(self, command, cwd=".", success_codes=(0,)):
        """Run a shell command."""
        if isinstance(command, list):
            command = ' '.join(command)
        self.log_point(f"Run Command='{command}', cwd={cwd}") if self.is_debug else False
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, cwd=cwd)
            status = 0
        except subprocess.CalledProcessError as error:
            output = error.output or b""
            status = error.returncode
            command = error.cmd

        if output:
            output = output.decode("utf-8")

        if status not in success_codes:
            raise Exception(
                colored(f'Command \'{command}\', returned {status}: \n>>{output}', "red")
            )
        self.log_point(f"[output] >> {output}") if self.is_debug else False
        return output

    def update_nested_dict(self, value, nvalue):
        if not isinstance(value, dict) or not isinstance(nvalue, dict):
            return nvalue
        for k, v in nvalue.items():
            value.setdefault(k, dict())
            if isinstance(v, dict):
                v = self.update_nested_dict(value[k], v)
            value[k] = v
        return value

    def _replace_compose_value(self, find_key=None, replace_value=None, nested_key=None, nested_value=None):
        if nested_key and nested_value:
            content_dict = nested_value
        else:
            content_dict = self.docker_compose_content
        for key, value in content_dict.items():
            if isinstance(value, dict):
                self._replace_compose_value(find_key=find_key, replace_value=replace_value, nested_key=key, nested_value=value)
            else:
                if key == find_key:
                    self.log_point(f"find key={key}, value={value}") if self.is_debug else False
                    content_dict[key] = replace_value
        return content_dict

    def copy_docker_compose(self, src_file="./docker-compose.yml", content=None):
        self.log_point() if self.is_debug else False
        docker_compose_path = self.get_compose_path()
        if content is None and self.docker_compose_content:
            content = self.docker_compose_content

        with open(src_file, 'r') as f:
            docker_compose_content = yaml.load(f, Loader=yaml.FullLoader)
            debug(before=docker_compose_content) if self.is_debug else False

            if content:
                self.docker_compose_content = self.update_nested_dict(docker_compose_content, content)
                self.docker_compose_content = self._replace_compose_value(find_key="image", replace_value=self.get_image_version())
                self.docker_compose_content = self._replace_compose_value(find_key="SERVICE", replace_value=self.get_service())
                debug(after=docker_compose_content) if self.is_debug else False
            os.system(f"mkdir -p {docker_compose_path}/config")
            self.write_docker_compose()

    def write_docker_compose(self):
        self.log_point() if self.is_debug else False
        if os.path.isdir(f"{self.get_compose_path()}/config") is False:
            os.system(f"mkdir -p {self.get_compose_path()}/config")

        with open(f"{self.get_compose_path()}/{self.docker_compose_file}", 'w') as outfile:
            yaml.dump(self.docker_compose_content, outfile)

    def docker_compose_execute(self, *sub_command):
        command = ["docker-compose"]
        if self.docker_compose_file != "docker-compose.yml":
            command += ["-f", self.docker_compose_file]
        command += sub_command
        self.log_point(f"docker_compose_execute => {command}") if self.is_debug else False
        return self.execute(command, cwd=self.get_compose_path())

    def _wait_until_responsive(self, check, timeout, pause, clock=timeit.default_timer, success_condition=True):
        """Wait until a service is responsive."""

        ref = clock()
        now = ref
        count = 1
        total_count = int(timeout / pause)
        function_name = get_lambda_name(check)
        self.log_point(function_name, "white")
        check_result = None
        check_result_text = None
        while (now - ref) < timeout:
            check_result = check()
            if check_result == success_condition:
                return
            time.sleep(pause)
            now = clock()

            try:
                check_result_text = check_result[1].text
            except:
                pass
            # self.log_point(f"{function_name} {message}" + "🦄" * count)
            # self.log_point(f"{function_name}({count}/{total_count}) {check_result}", "white")
            self.log_point(f"({count}/{total_count}) {check_result}", "white")
            count += 1
        print("")
        self.execute(f"docker logs {self.compose_service_name} -n 40")
        raise Exception(f"Timeout reached while waiting on service! \n {check_result}, {check_result_text}")

    def _is_responsive(self, url):
        try:
            try:
                response = requests.get(url)
                if response.status_code == 200 and response.json() != []:
                    self.log_point("Ready for service", "white")
                    return True
            except:
                return False
        except ConnectionError:
            return False

    def _check_blockheight(self, url="http://localhost:9000/admin/chain", reach_block=20):
        try:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    response_json = response.json()[0]
                    if self.blockheight_info['first'] == 0:
                        self.blockheight_info['first'] = response_json["height"]

                    if self.blockheight_info['last'] >= 0:
                        self.blockheight_info['last'] = response_json["height"]

                    if (self.blockheight_info['last'] - self.blockheight_info['first']) >= reach_block:
                        self.log_point(f"reach blockheight = {self.blockheight_info}", "white")
                        return True

                    return False, response
            except Exception as e:
                return False, e
        except ConnectionError:
            return False

    def wait_until_blockheight(self, timeout=60, pause=1, reach_block=20):
        self._wait_until_responsive(
            timeout=timeout,
            pause=pause,
            check=lambda: self._check_blockheight(reach_block=reach_block)
        )

    def start_container(self, wait=True):
        self.log_point(f"docker-compose path = {self.get_compose_path()}")
        self.log_point() if self.is_debug else False
        self.docker_compose_execute("up", "-d")

        if wait:
            self.log_point(f"Wait for container.  image={self.image_version}, container={self.compose_service_name}, service={self.service}")

            docker_compose_content = yaml.dump_all([self.docker_compose_content])
            print_syntax(docker_compose_content, "yaml")

            self._wait_until_responsive(
                timeout=30,
                pause=1,
                check=lambda: self._is_responsive("http://localhost:9000/admin/chain")
            )

    def stop_container(self):
        self.log_point() if self.is_debug else False
        self.docker_compose_execute("down", "-v")

    def exec_container(self, sub_command, expected_output=None):
        """
        Run a shell command in container
        :param sub_command:
        :param expected_output:
        :return:
        """
        self.log_point() if self.is_debug else False
        if self.compose_service_name and self.compose_service_name is not None:
            default_cmd = f"exec {self.compose_service_name}"
        else:
            default_cmd = "exec"

        # command = (default_cmd, *sub_command)
        command = (default_cmd, f"bash -c '{sub_command}'")
        output = self.docker_compose_execute(*command)

        if expected_output and output:
            match = re.findall(expected_output, output)
            message = f"expected_output={expected_output}, output={output}"
            if len(match) > 0:
                self.log_point(f"Matched, {message}", "green") if self.is_debug else False
            else:
                raise Exception(colored(f"Not matched, {message}", "red"))
        return output

    def control_chain_join(self):
        if self.seed_domain:
            self.log_point(f"seed = {self.seed_domain}", "white")
            self.exec_container(f"control_chain join --seedAddress {self.seed_domain}")

            if self.service == "MainNet":
                self.exec_container(f"cp /ctx/mainnet_v1_block_proof/block_v1_proof.bin ${{GOLOOP_DATA_ROOT}}/1/")
        else:
            raise Exception(colored(f"Seed not found - {self.service}", "red"))

    def get_goloop_version(self):
        # goloop_version = self.execute("make version").strip()
        return self.version

    def get_image_version(self):
        # image_version = self.execute("make image_version").strip()
        return self.image_version

    def get_service(self):
        # service = self.execute("make service").strip()
        return self.service

    def get_seed_domain(self):
        base_domain = "solidwallet.io:7100"
        if self.service == "MainNet":
            short_name = "ctz"
        else:
            short_name = self.service.lower().replace("net", "")
        return f"seed-{short_name}.{base_domain}"

    def get_compose_path(self):
        return f"{os.path.dirname(os.path.realpath(__file__))}/{self.container_path}"

    def initialize(self):
        # self.log_point(f"Initialize ", "white")
        if len(self.make_args) == 0:
            self._get_make_args()

        if not self.service:
            self.service = self.make_args.get("SERVICE", "MainNet")
        if not self.version:
            self.version = self.make_args.get("VERSION")
        if not self.tag_name:
            self.tag_name = self.make_args.get("TAGNAME")

        if not self.image_version:
            self.image_version = f"{self.make_args.get('REPO_HUB')}/{self.make_args.get('NAME')}:{self.tag_name}"
        if not self.seed_domain:
            self.seed_domain = self.get_seed_domain()
        if self.make_args.get("DEBUG"):
            self.is_debug = converter.str2bool(self.make_args.get("DEBUG"))
        debug(self.__dict__) if self.is_debug else False
        return self

    def _get_make_args(self):
        make_args_output = self.execute("make make_build_args USE_COLOR=false")
        for line in make_args_output.split("\n"):
            if "=" in line:
                line_list = line.split("=")
                key = line_list[0].strip()
                value = line_list[1].strip()
                self.make_args[key] = value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.initialize()
        # classdump(self)

    @classmethod
    def setUpClass(cls) -> None:
        """
        Preparing works for each TestSuite
        :return:
        """
        class_obj = cls()
        class_obj.initialize()
        # sys.exit()
        if class_obj.is_control_container:

            if os.path.isfile(f"{class_obj.docker_compose_path}/{class_obj.docker_compose_file}"):
                class_obj.log_point("Stop container already running")
                class_obj.docker_compose_execute("down")

            if class_obj.is_reset_container_path:
                if os.path.isdir(class_obj.get_compose_path()):
                    class_obj.execute(f"rm -rf {class_obj.get_compose_path()}")
                    class_obj.log_point(f"Remove the {class_obj.get_compose_path()}") if class_obj.is_debug else False

            if class_obj.is_from_compose_template:
                class_obj.copy_docker_compose()
            else:
                class_obj.write_docker_compose()
            class_obj.start_container()

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Shutdown works for each TestSuite
        :return:
        """
        class_obj = cls()
        class_obj.docker_compose_execute("logs", "--tail 20")
        if class_obj.is_control_container:
            class_obj.stop_container()

    def setUp(self) -> None:
        """
        Preparing works for each TestCase
        :return:
        """
        self.initialize()
        pass

    def tearDown(self) -> None:
        """
        Shutdown works for each TestCase
        :return:
        """
        pass


class TestRunner:
    def __init__(self, module="__main__", config=None):
        self.module = module
        if isinstance(module, str):
            self.module = __import__(module)
            for part in module.split('.')[1:]:
                self.module = getattr(self.module, part)
        else:
            self.module = module
        self.test = unittest.defaultTestLoader.loadTestsFromModule(self.module)

    def run(self, verbosity=2):
        try:
            ret = ContainerTestRunner(verbosity=verbosity).run(self.test).wasSuccessful()
            sys.exit(not ret)

        except KeyboardInterrupt:
            for test_suite in get_test_suites(self.module, "__main__"):
                if isinstance(test_suite, type) and issubclass(test_suite, ContainerTestCase):
                    ts_cls = test_suite()
                    ts_cls.stop_container()
                    ts_cls.log_point(f"{ts_cls} KeyboardInterrupt, It will be terminated container", "red")
                    ts_cls.stop_container()
                    ts_cls.log_point(f"{ts_cls} Terminated container", "red")


class ContainerTestResult(unittest.runner.TextTestResult):
    """
    This class modifies the result value of TestSuites.
    Extension of TextTestResult to support numbering test cases.
    """

    def __init__(self, stream, descriptions, verbosity):
        """Initializes the test number generator, then calls super impl"""

        self.test_numbers = itertools.count(1)

        return super(ContainerTestResult, self).__init__(stream, descriptions, verbosity)

    def startTest(self, test):
        """Writes the test number to the stream if showAll is set, then calls super impl"""

        if self.showAll:
            progress = '\n 🦄 [{0}/{1}] '.format(next(self.test_numbers), self.test_case_count)
            self.stream.write(progress)

            # Also store the progress in the test itself, so that if it errors,
            # it can be written to the exception information by our overridden
            # _exec_info_to_string method:
            test.progress_index = progress

        return super(ContainerTestResult, self).startTest(test)

    def addError(self, test, err):
        if self.showAll:
            self.stream.writeln(colored("ERROR", "red"))
        elif self.dots:
            self.stream.write(colored('E', "red"))
            self.stream.flush()
        return super(unittest.runner.TextTestResult, self).addError(test, err)
        # return super(ContainerTestResult, self).addError(test, err)

    def _exc_info_to_string(self, err, test):
        """Gets an exception info string from super, and prepends 'Test Number' line"""

        info = super(ContainerTestResult, self)._exc_info_to_string(err, test)
        # setUpClass has not progress_index attr
        try:
            if not getattr(test, 'progress_index'):
                test.progress_index = 0
        except:
            test.progress_index = 0

        if self.showAll:
            info = 'Test number: {index}\n{info}'.format(
                index=test.progress_index,
                info=info
            )

        return info


class ContainerTestRunner(unittest.runner.TextTestRunner):
    """
    This class modifies the result value of TestSuites.
    Extension of TextTestResult to support numbering test cases.
    """

    resultclass = ContainerTestResult

    def run(self, test):
        """Stores the total count of test cases, then calls super impl"""

        self.test_case_count = test.countTestCases()
        return super(ContainerTestRunner, self).run(test)

    def _makeResult(self):
        """Creates and returns a result instance that knows the count of test cases"""

        result = super(ContainerTestRunner, self)._makeResult()
        result.test_case_count = self.test_case_count
        return result


def classdump(obj):
    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'
    for attr in dir(obj):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            print(bcolors.OKGREEN + f"obj.{attr} = " +
                  bcolors.WARNING + f"{value}" + bcolors.ENDC)


def get_test_suites(module=None, location="__main__"):
    """
    Get a list of Test suites. (Class)
    :param module:
    :param location:
    :return: list
    """
    if module is None:
        module = sys.modules[__name__]
    return_list = []

    for name, obj in inspect.getmembers(module):
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase):
            if location:
                if location == obj.__module__:
                    return_list.append(obj)
            else:
                return_list.append(obj)
    return return_list


def get_lambda_name(func):
    remove_strings = ["lambda: "]
    func_name = inspect.getsource(func).split('=')[1].strip()
    if "(" in func_name:
        func_name = func_name.split("(")[0]

    for string in remove_strings:
        func_name = func_name.replace(string, "")

    return func_name


def get_globals():
    parent_module = sys.modules['.'.join(__name__.split('.')[:-1]) or '__main__']
    return parent_module


def set_os_env(home_path: str):
    os.environ['CONFIG_URL'] = "https://networkinfo.solidwallet.io/node_info"
    os.environ['SERVICE'] = "MainNet"
    os.environ['CONFIG_URL_FILE'] = "default_configure.yml"
    os.environ['CONFIG_LOCAL_FILE'] = f"{home_path}/goloop/configure.yml"
    os.environ['LOCAL_TEST'] = "False"
    os.environ['BASE_DIR'] = f"{home_path}/goloop"
    os.environ['ONLY_GOLOOP'] = "False"
    os.environ['GOLOOP_P2P_LISTEN'] = ":7100"
    os.environ['GOLOOP_RPC_ADDR'] = ":9000"
    os.environ['DOCKER_LOG_FILES'] = "chain.log,health.log,error.log,debug.log"
    os.environ['CHECK_STACK_LIMIT'] = "1"
    temp_env = dict()
    temp_env['CONFIG_URL'] = os.getenv('CONFIG_URL', 'https://networkinfo.solidwallet.io/node_info')
    temp_env['SERVICE'] = os.getenv('SERVICE', 'MainNet')
    temp_env['CONFIG_URL_FILE'] = os.getenv('CONFIG_URL_FILE', 'default_configure.yml')
    temp_env['CONFIG_LOCAL_FILE'] = os.getenv('CONFIG_LOCAL_FILE', '/goloop/configure.yml')
    temp_env['LOCAL_TEST'] = converter.str2bool(os.getenv('LOCAL_TEST', False))
    temp_env['BASE_DIR'] = os.getenv('BASE_DIR', '/goloop')
    temp_env['ONLY_GOLOOP'] = converter.str2bool(os.getenv('ONLY_GOLOOP', False))
    return temp_env


def set_docker_compose(home_path: str):
    docker_compose = {
        'version': '3',
        'services': {
            'icon2-node': {
                'image': 'iconloop/goloop-icon:latest',
                'container_name': 'icon2-node',
                'restart': 'on-failure',
                'network_mode': 'host',
                'environment': {
                    'GENESIS_STORAGE': '/goloop/config/icon_genesis.zip',
                    'MAX_BLOCK_TX_BYTES': '2048000',
                    'NORMAL_TX_POOL': '10000',
                    'ROLE': '0',
                    'GOLOOP_ENGINES': 'python',
                    'GOLOOP_P2P_LISTEN': ':7100',
                    'GOLOOP_RPC_DUMP': 'false',
                    'GOLOOP_CONSOLE_LEVEL': 'debug',
                    'GOLOOP_LOG_LEVEL': 'trace',
                    'GOLOOP_LOGFILE': '/goloop/logs/goloop.log',
                    'GOLOOP_LOG_WRITER_FILENAME': '/goloop/logs/goloop.log',
                    'GOLOOP_LOG_WRITER_COMPRESS': 'true',
                    'GOLOOP_LOG_WRITER_LOCALTIME': 'true',
                    'GOLOOP_LOG_WRITER_MAXAGE': '0',
                    'GOLOOP_LOG_WRITER_MAXSIZE': '1024',
                    'GOLOOP_LOG_WRITER_MAXBACKUPS': '7',
                    'SEEDS': 'seed.ctz.solidwallet.io:7100',
                    'GOLOOP_P2P': '52.78.213.121:7100',
                    'GOLOOP_RPC_ADDR': ':9000',
                    'CID': '0x1'
                },
                'cap_add': ['SYS_TIME'],
                'volumes': ['./config:/goloop/config',
                            './data:/goloop/data',
                            './logs:/goloop/logs']
            }
        }
    }
    _url = "http://checkip.amazonaws.com"
    os.system(f"mkdir -p {home_path}/goloop/config")
    with urlopen(_url) as res:
        public_ip = res.read().decode().replace('\n', '')
    port = docker_compose['services']['icon2-node']['environment'].get('GOLOOP_P2P_LISTEN', ':8080').split(':')[-1]
    docker_compose['services']['icon2-node']['environment']['GOLOOP_P2P'] = f"{public_ip}:{port}"
    with open(f"{home_path}/goloop/docker-compose.yml", 'w') as outfile:
        yaml.dump(docker_compose, outfile)
    os.system(f"curl -o {home_path}/goloop/config/icon_genesis.zip https://networkinfo.solidwallet.io/icon2/MainNet/icon_genesis.zip")
    return docker_compose
