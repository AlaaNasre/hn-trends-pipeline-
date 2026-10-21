from unittest.mock import Mock, patch
import requests
from src.fetch import get

def test_get_none_after_three_failures():
    session=Mock()
    session.get.side_effect=requests.ConnectionError("offline")
    with patch("src.fetch.time.sleep"):
        assert get("topstories",session=session) is None
    assert session.get.call_count==3

def test_get_timeout_and_json():
    session=Mock()
    response=Mock()
    response.json.return_value={"ok":True}
    session.get.return_value=response
    assert get("item/1",session=session)=={"ok":True}
    session.get.assert_called_once_with("https://hacker-news.firebaseio.com/v0/item/1.json",timeout=10.0)
