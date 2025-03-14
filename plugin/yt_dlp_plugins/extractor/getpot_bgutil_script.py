from __future__ import annotations

import json
import os.path
import shutil
import subprocess
import typing

if typing.TYPE_CHECKING:
    from yt_dlp import YoutubeDL
from yt_dlp.networking._helper import select_proxy
from yt_dlp.networking.exceptions import RequestError
from yt_dlp.utils import Popen, classproperty

try:
    from yt_dlp_plugins.extractor.getpot_bgutil import BgUtilBaseGetPOTRH, getpot
except ImportError:
    pass
else:

    @getpot.register_provider
    class BgUtilScriptGetPOTRH(BgUtilBaseGetPOTRH):
        @classproperty(cache=True)
        def _default_script_path(self):
            for base_path in [
                os.environ.get('XDG_CONFIG_HOME', ''),
                os.path.expanduser('~/.config'),
                os.path.expanduser('~'),
            ]:
                script_path = os.path.join(
                    base_path,
                    'bgutil-ytdlp-pot-provider',
                    'server',
                    'build',
                    'generate_once.js',
                )
                if os.path.exists(script_path):
                    return script_path
            return script_path

        def _validate_get_pot(
            self,
            client: str,
            ydl: YoutubeDL,
            visitor_data=None,
            data_sync_id=None,
            player_url=None,
            **kwargs,
        ):
            script_path = ydl.get_info_extractor('Youtube')._configuration_arg(
                'getpot_bgutil_script',
                [self._default_script_path],
                casesense=True,
            )[0]
            if not data_sync_id and not visitor_data:
                self.warn_and_raise('One of [data_sync_id, visitor_data] must be passed')
            if not os.path.isfile(script_path):
                self.warn_and_raise(f"Script path doesn't exist: {script_path}")
            if os.path.basename(script_path) != 'generate_once.js':
                self.warn_and_raise('Incorrect script passed to extractor args. Path to generate_once.js required')
            if shutil.which('node') is None:
                self.warn_and_raise('node is not in PATH')
            self.script_path = script_path

        def _get_pot(
            self,
            client: str,
            ydl: YoutubeDL,
            visitor_data=None,
            data_sync_id=None,
            player_url=None,
            **kwargs,
        ) -> str:
            self._logger.info(f'Generating POT via script: {self.script_path}')
            command_args = ['node', self.script_path]
            if proxy := select_proxy('https://jnn-pa.googleapis.com', self.proxies):
                if proxy != select_proxy('https://youtube.com', self.proxies):
                    self._logger.warning(
                        'Proxies for https://youtube.com and https://jnn-pa.googleapis.com are different. '
                        'This is likely to cause subsequent errors.',
                    )
                command_args.extend(['-p', proxy])
            if data_sync_id:
                command_args.extend(['-d', data_sync_id])
            elif visitor_data:
                command_args.extend(['-v', visitor_data])
            else:
                raise RequestError('Unexpected missing visitorData and dataSyncId in _get_pot_via_script')
            self._logger.debug(f'Executing command to get POT via script: {" ".join(command_args)}')

            try:
                stdout, stderr, returncode = Popen.run(
                    command_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self._GETPOT_TIMEOUT,
                )
            except subprocess.TimeoutExpired as e:
                raise RequestError(
                    f'_get_pot_via_script failed: Timeout expired when trying to run script (caused by {e!r})',
                )
            except Exception as e:
                raise RequestError(f'_get_pot_via_script failed: Unable to run script (caused by {e!r})') from e

            msg = f'stdout:\n{stdout.strip()}'
            if stderr.strip():  # Empty strings are falsy
                msg += f'\nstderr:\n{stderr.strip()}'
            self._logger.debug(msg)
            if returncode:
                raise RequestError(f'_get_pot_via_script failed with returncode {returncode}')

            try:
                # The JSON response is always the last line
                script_data_resp = json.loads(stdout.splitlines()[-1])
            except json.JSONDecodeError as e:
                raise RequestError(f'Error parsing JSON response from _get_pot_via_script (caused by {e!r})') from e
            else:
                self._logger.debug(f'_get_pot_via_script response = {script_data_resp}')
            if potoken := script_data_resp.get('poToken'):
                return potoken
            else:
                raise RequestError('The script did not respond with a po_token')

    @getpot.register_preference(BgUtilScriptGetPOTRH)
    def bgutil_script_getpot_preference(rh, request):
        return 100

    __all__ = [BgUtilScriptGetPOTRH.__class__.__name__, bgutil_script_getpot_preference.__name__]
