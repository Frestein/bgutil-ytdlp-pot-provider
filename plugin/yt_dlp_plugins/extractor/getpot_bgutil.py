from __future__ import annotations

__version__ = '0.7.3'

import os
import time
import typing

if typing.TYPE_CHECKING:
    from yt_dlp import YoutubeDL
from yt_dlp.networking.common import Features
from yt_dlp.networking.exceptions import UnsupportedRequest
from yt_dlp.utils import classproperty, remove_end

try:
    import yt_dlp_plugins.extractor.getpot as getpot
except ImportError as e:
    e.msg += '\nyt-dlp-get-pot is missing! See https://github.com/coletdjnz/yt-dlp-get-pot?tab=readme-ov-file#installing.'
    raise e


class BgUtilBaseGetPOTRH(getpot.GetPOTProvider):
    _SUPPORTED_CLIENTS = ('web', 'web_safari', 'web_embedded',
                          'web_music', 'web_creator', 'mweb', 'tv_embedded', 'tv')
    VERSION = __version__
    _SUPPORTED_PROXY_SCHEMES = (
        'http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h')
    _SUPPORTED_FEATURES = (Features.NO_PROXY, Features.ALL_PROXY)
    _SUPPORTED_CONTEXTS = ('gvs', 'player')
    _GETPOT_TIMEOUT = 20.0
    _GETPOT_ENV = {
        **os.environ,
        'TOKEN_TTL': '0',
    }
    _CACHE_STORE = 'youtube-getpot-bgutil'
    _CACHE_STORE_KEY = 'po_token'
    _DEFAULT_CACHE_TTL_SECONDS = {
        'gvs': 6 * 60 * 60,
        'player': 10 * 60,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.yt_ie = None
        self.content_binding = None

    def _get_config_setting(self, key, casesense=True, default=None):
        return self.yt_ie._configuration_arg(key, [default], ie_key=f'youtube-{self.RH_NAME.lower()}', casesense=casesense)[0]

    def _warn_and_raise(self, msg, once=True, raise_from=None):
        self._logger.warning(msg, once=once)
        raise UnsupportedRequest(msg) from raise_from

    @staticmethod
    def _get_content_binding(client, context, data_sync_id=None, visitor_data=None, video_id=None):
        # https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide#po-tokens-for-player
        if context == 'gvs' or client == 'web_music':
            # web_music player or gvs is bound to data_sync_id or visitor_data
            return data_sync_id or visitor_data

        return video_id

    @classmethod
    def _clear_expired_cache(cls, ie) -> dict:
        cached_tokens = cls._get_cached_tokens(ie)
        return {k: v for k, v in cached_tokens.items() if v['expires_at'] > time.time()}

    @classmethod
    def get_cache_ttl(cls, context):
        return cls._DEFAULT_CACHE_TTL_SECONDS.get(context, 0)

    def _cache_token(self, po_token, expires_at=None, *,
                     content_binding, context='gvs'):
        cached_tokens = self._clear_expired_cache(self.yt_ie)
        cached_tokens[content_binding] = {
            'po_token': po_token,
            'expires_at': time.time() + self.get_cache_ttl(context=context) if expires_at is None else expires_at,
            'version': self.VERSION,
        }
        self.yt_ie.cache.store(self._CACHE_STORE, self._CACHE_STORE_KEY, cached_tokens)
        return po_token

    @classmethod
    def _get_cached_tokens(cls, ie) -> dict:
        return ie.cache.load(cls._CACHE_STORE, cls._CACHE_STORE_KEY) or {}

    def _get_cached_token(self, context, content_binding):
        token_data = self._get_cached_tokens(self.yt_ie).get(content_binding)
        if not token_data:
            return None
        if token_data['expires_at'] < time.time():
            self._logger.debug(f'Cached {context} PO Token expired')
            return None

        pot = token_data['po_token']
        self._logger.debug(f'Retrieved {context} PO Token from cache: {pot}')
        return pot

    def _validate_get_pot(
        self,
        client: str,
        ydl: YoutubeDL,
        visitor_data=None,
        data_sync_id=None,
        context=None,
        video_id=None,
        **kwargs,
    ):
        # sets yt_ie, content_binding
        self.yt_ie = ydl.get_info_extractor('Youtube')
        self.content_binding = self._get_content_binding(
            client=client, context=context, data_sync_id=data_sync_id,
            visitor_data=visitor_data, video_id=video_id)
        self._real_validate_get_pot(
            client=client, ydl=ydl, visitor_data=visitor_data,
            data_sync_id=data_sync_id, context=context, video_id=video_id,
            **kwargs)

    def _real_validate_get_pot(
        self,
        client: str,
        ydl: YoutubeDL,
        visitor_data=None,
        data_sync_id=None,
        context=None,
        video_id=None,
        **kwargs,
    ):
        """
        Validate and check the GetPOT request is supported.
        """

    @classproperty
    def RH_NAME(cls):
        return cls._PROVIDER_NAME or remove_end(cls.RH_KEY, 'GetPOT')


@getpot.register_provider
class BgUtilCacheGetPOTRH(BgUtilBaseGetPOTRH):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_pot = None

    def _real_validate_get_pot(
        self,
        client: str,
        ydl: YoutubeDL,
        visitor_data=None,
        data_sync_id=None,
        session_index=None,
        player_url=None,
        context=None,
        video_id=None,
        ytcfg=None,
        **kwargs,
    ):
        if (cached_pot := self._get_cached_token(
                context=context,
                content_binding=self.content_binding)) is not None:
            self.cached_pot = cached_pot
        else:
            self.cached_pot = None
            raise UnsupportedRequest('No cache available')

    def _get_pot(
        self,
        client: str,
        ydl: YoutubeDL,
        visitor_data=None,
        data_sync_id=None,
        session_index=None,
        player_url=None,
        context=None,
        video_id=None,
        ytcfg=None,
        **kwargs,
    ) -> str:
        return self.cached_pot


@getpot.register_preference(BgUtilCacheGetPOTRH)
def bgutil_cache_getpot_preference(rh, request):
    return 200


__all__ = [BgUtilCacheGetPOTRH, getpot.__name__, '__version__']
