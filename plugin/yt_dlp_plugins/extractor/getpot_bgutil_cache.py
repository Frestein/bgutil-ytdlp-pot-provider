from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from yt_dlp import YoutubeDL
from yt_dlp.networking.exceptions import UnsupportedRequest

try:
    from yt_dlp_plugins.extractor.getpot_bgutil import BgUtilBaseGetPOTRH, getpot
except ImportError:
    pass
else:
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
                raise UnsupportedRequest('Cache miss')

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

    __all__ = [BgUtilCacheGetPOTRH.__class__.__name__, bgutil_cache_getpot_preference.__name__]
