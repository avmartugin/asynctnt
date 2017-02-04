import asyncio
import asyncio.subprocess
import logging
import math
import os
import random
import shutil
import string

import functools
import psutil


__all__ = (
    'TarantoolInstanceProtocol', 'TarantoolInstance'
)


class TarantoolInstanceProtocol(asyncio.SubprocessProtocol):
    def __init__(self, tnt, on_exit):
        super().__init__()
        self._tnt = tnt
        self._on_exit = on_exit
        self._transport = None

    @property
    def logger(self):
        return self._tnt.logger

    @property
    def pid(self):
        return self._transport.get_pid() if self._transport else None

    def connection_made(self, transport):
        self.logger.info('Process started')
        self._transport = transport

    def pipe_data_received(self, fd, data):
        if not data:
            return
        line = data.decode()
        line = line.replace('\r', '')
        lines = line.split('\n')
        for line in lines:
            line = line.replace('\n', '')
            line = line.strip()
            if line:
                self.logger.info('=> {}'.format(line))

    def process_exited(self):
        return_code = self._transport.get_returncode()
        if callable(self._on_exit):
            self._on_exit(return_code)

    @property
    def returncode(self):
        return self._transport.get_returncode()

    async def wait(self):
        """Wait until the process exit and return the process return code.

        This method is a coroutine."""
        return await self._transport._wait()

    def send_signal(self, signal):
        self._transport.send_signal(signal)

    def terminate(self):
        self._transport.terminate()

    def kill(self):
        self._transport.kill()


class TarantoolInstance:
    def __init__(self, *,
                 host='127.0.0.1',
                 port=3301,
                 console_port=3302,
                 replication_source=None,
                 title=None,
                 logger=None,
                 log_level=5,
                 slab_alloc_arena=0.1,
                 wal_mode='none',
                 root=None,
                 cleanup=True,
                 initlua_template=None,
                 applua='-- app.lua --',
                 timeout=5.,
                 loop=None
                 ):
        """

        :param host: The host which Tarantool instance is going
                     to be listening on (default = 127.0.0.1)
        :param port: The port which Tarantool instance is going
                     to be listening on (default = 3301)
        :param console_port: The port which Tarantool console is going
                             to be listening on (to execute admin commands)
                             (default = 3302)
        :param replication_source: The replication source string.
                                   If it's None, then replication_source=nil
                                   in box.cfg
        :param title: Tarantool instance title (substitutes
                      into custom_proc_title). (default = "tnt[host:port]")
        :param logger: logger, where all messages are logged to.
                       default logger name = Tarantool[host:port]
        :param log_level: Tarantool's log_level (default = 5)
        :param slab_alloc_arena: Tarantool's slab_alloc_arena (default = 0.1)
        :param wal_mode: Tarantool's wal_mode (default = 'none')
        :param root: Tarantool's work_dir location
        :param cleanup: do cleanup or not
        :param initlua_template: The initial init.lua template
                                 (default can be found in
                                 _create_initlua_template function)
        :param applua: Any extra lua script (a string)
                       (default = '-- app.lua --')
        :param timeout: Timeout in seconds - how much to wait for tarantool
                        to become active
        :param loop: loop instance
        """
        self._loop = loop or asyncio.get_event_loop()

        self._host = host
        self._port = port
        self._console_port = console_port
        self._replication_source = replication_source
        self._title = title or self._generate_title()
        self._logger = logger or logging.getLogger(self.fingerprint)
        self._log_level = log_level
        self._slab_alloc_arena = slab_alloc_arena
        self._wal_mode = wal_mode
        self._root = root or self._generate_root_folder_name()
        self._cleanup = cleanup

        self._initlua_template = initlua_template or \
            self._create_initlua_template()
        self._applua = applua

        self._timeout = timeout

        self._is_running = False
        self._is_stopping = False
        self._transport = None
        self._protocol = None
        self._last_return_code = None
        self._stop_event = asyncio.Event(loop=self._loop)

    def _random_string(self,
                       length, *,
                       source=string.ascii_uppercase +
                       string.ascii_lowercase +
                       string.digits):
        return ''.join(random.choice(source) for _ in range(length))

    def _generate_title(self):
        return 'tnt[{}:{}]'.format(self._host, self._port)

    def _generate_root_folder_name(self):
        cwd = os.getcwd()
        path = None
        while path is None or os.path.isdir(path):
            folder_name = '__tnt__' + self._title + \
                          '_' + self._random_string(10)
            path = os.path.join(cwd, folder_name)
        return path

    def _create_initlua_template(self):
        return """
            box.cfg{
              listen = "${host}:${port}",
              wal_mode = "${wal_mode}",
              custom_proc_title = "${custom_proc_title}",
              slab_alloc_arena = ${slab_alloc_arena},
              replication_source = ${replication_source},
              work_dir = "${work_dir}",
              log_level = ${log_level}
            }
            box.schema.user.grant("guest", "read,write,execute", "universe")
            require('console').listen("${host}:${console_port}")
            ${applua}
        """

    def _render_initlua(self):
        template = string.Template(self._initlua_template)
        d = {
            'host': self._host,
            'port': self._port,
            'console_port': self._console_port,
            'wal_mode': self._wal_mode,
            'custom_proc_title': self._title,
            'slab_alloc_arena': self._slab_alloc_arena,
            'replication_source': 'nil' if not self._replication_source else '"{}"'.format(self._replication_source),  # nopep8
            'work_dir': self._root,
            'log_level': self._log_level,
            'applua': self._applua if self._applua else ''
        }
        return template.substitute(d)

    def _save_initlua(self, initlua):
        initlua = initlua.replace(' ' * 4, '')
        initlua_path = os.path.join(self._root, 'init.lua')
        with open(initlua_path, 'w') as f:
            f.write(initlua)
        return initlua_path

    @property
    def logger(self):
        return self._logger

    @property
    def fingerprint(self):
        return 'Tarantool[{}:{}]'.format(self._host, self._port)

    def prepare(self):
        self._last_return_code = None
        self._stop_event.clear()
        os.mkdir(self._root)
        initlua = self._render_initlua()
        initlua_path = self._save_initlua(initlua)
        return initlua_path

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def console_port(self):
        return self._console_port

    @property
    def is_running(self):
        return self._is_running

    @property
    def pid(self):
        return self._protocol.pid if self._protocol else None

    def _on_process_exit(self, return_code):
        self._last_return_code = return_code
        if self._is_stopping:
            return
        self._stop_event.set()
        self.cleanup()

    async def wait_stopped(self):
        return await self._stop_event.wait()

    async def start(self):
        self._logger.info(
            'Starting Tarantool instance ({})'.format(self._title))
        initlua_path = self.prepare()
        self._logger.info('Launching process')

        factory = functools.partial(
            TarantoolInstanceProtocol, self, self._on_process_exit)
        self._transport, self._protocol = await self._loop.subprocess_exec(
            factory,
            'tarantool', initlua_path,
            stdin=None,
            stderr=asyncio.subprocess.PIPE,
        )

        procinfo = psutil.Process(self.pid)
        interval = 0.1
        attempts = math.ceil(self._timeout / interval)
        while attempts > 0:
            if self._protocol is None or self._protocol.returncode is not None:
                raise RuntimeError(
                    '{} exited unexpectedly with exit code {}'.format(
                        self.fingerprint, self._last_return_code)
                )
            cmdline = procinfo.cmdline()
            if cmdline:
                cmdline = cmdline[0]
                if 'running' in cmdline:
                    self._logger.info('Moved to the running state')
                    break
            await asyncio.sleep(interval, loop=self._loop)
            attempts -= 1
        else:
            raise asyncio.TimeoutError(
                'Timeout while waiting for Tarantool to move to running state')
        self._is_running = True

    async def stop(self):
        if self._protocol is not None:
            self._is_stopping = True
            self._protocol.terminate()
            await self._stop()

    def terminate(self):
        if self._protocol is not None:
            self._is_stopping = True
            self._protocol.terminate()
            self.cleanup()

    def kill(self):
        if self._protocol is not None:
            self._is_stopping = True
            self._protocol.kill()
            self.cleanup()

    async def _stop(self):
        if not self._is_running:
            return

        self._logger.info('Waiting for process to complete')
        await self._protocol.wait()
        self.cleanup()

    def cleanup(self):
        return_code = self._protocol.returncode
        self._logger.info('Finished with return code {}'.format(return_code))

        self._is_running = False
        self._is_stopping = False
        self._transport = None
        self._protocol = None
        self._stop_event.clear()
        if self._cleanup:
            shutil.rmtree(self._root, ignore_errors=True)
        self._logger.info(
            'Destroyed Tarantool instance ({})'.format(self._title))

    def __del__(self):
        self.terminate()
