from importlib.metadata import PackageNotFoundError, version

name = "nba_api"
try:
    __version__ = version("nba_api")
except PackageNotFoundError:
    __version__ = "0+local"
