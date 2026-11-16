"""Vercel Python function: reuse the standalone service and policy unchanged."""
import os
from server import Handler, validate_public_origin

PUBLIC_ORIGIN = validate_public_origin(os.environ.get(
    'PUBLIC_ORIGIN', 'https://allowance-guard-thetom.vercel.app'))


class handler(Handler):
    def expected_origin(self):
        # Never infer trust from user-controlled Host or forwarded headers.
        return PUBLIC_ORIGIN
