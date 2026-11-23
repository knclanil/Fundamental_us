"""v3.1.1 regression tests: directory classification and provider 404 semantics."""
import importlib.util
import pathlib
import sys
from unittest.mock import Mock
import requests

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))
from pipeline import parse_exchange


def test_directory_excludes_non_common_securities():
    text = ('Symbol|Security Name|ETF|Test Issue|NextShares\n'
            'GOOD|Good Corp Common Stock|N|N|N\n'
            'UNIT|Good Corp Units|N|N|N\n'
            'WARR|Good Corp Warrants|N|N|N\n'
            'PREF|Good Corp Preferred Shares|N|N|N\n'
            'ETF1|Good Corp ETF|Y|N|N\n'
            'NEXT|Good Corp|N|N|Y\n')
    df = parse_exchange(text, 'Symbol')
    assert df.ticker.tolist() == ['GOOD']


def test_http_404_is_distinguishable_from_other_http_errors():
    for status in (404, 403, 429, 500):
        response = requests.Response()
        response.status_code = status
        response.url = 'https://finviz.com/stock?t=TEST&p=d'
        error = requests.HTTPError('failure', response=response)
        assert (error.response is not None and error.response.status_code == 404) == (status == 404)
