from .brute_force import brute_force
from .flood import flood_detector 
from .directory_scanner import directory_scanner_detector
from .user_agent_switching import ua_switching_detector
from .sus_uri import sus_uri_detector
from .xss_attempt import xss_detector


ALL_DETECTORS = (
    brute_force,
    flood_detector,
    directory_scanner_detector,
    ua_switching_detector,
    sus_uri_detector,
    xss_detector,
)