__version__ = '0.7.3'
import os
import time

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
    _CACHE_TTL_SECONDS = 6 * 60 * 60

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
    def _cache_token(cls, ie, po_token, expires_at=None, *, content_binding):
        token_data = {
            'po_token': po_token,
            'expires_at': time.time() + cls._CACHE_TTL_SECONDS if expires_at is None else expires_at,
            'version': cls.VERSION,
        }

        cached_tokens = cls._clear_expired_cache(ie)
        cached_tokens[content_binding] = token_data
        ie.cache.store(cls._CACHE_STORE, cls._CACHE_STORE_KEY, cached_tokens)
        return po_token

    @classmethod
    def _get_cached_tokens(cls, ie) -> dict:
        return ie.cache.load(cls._CACHE_STORE, cls._CACHE_STORE_KEY) or {}

    def _get_cached_token(self, ie, context, content_binding):
        key = content_binding
        token_data = self._get_cached_tokens(ie).get(key)

        if not token_data:
            return None

        if token_data['expires_at'] < time.time():
            self._logger.debug(f'Cached {context} PO Token expired')
            return None
        pot = token_data['po_token']
        self._logger.debug(f'Retrieved {context} PO Token from cache: {pot}')
        return pot

    @classproperty
    def RH_NAME(cls):
        return cls._PROVIDER_NAME or remove_end(cls.RH_KEY, 'GetPOT')


__all__ = [getpot.__name__, '__version__']
