"""About Dialog 关于对话框单元测试。"""

from ui.about_dialog import AboutDialog, _VERSION, _AUTHOR, _GITHUB_URL, _LICENSE


class TestAboutDialogData:
    """测试关于对话框的数据常量。"""

    def test_version_format(self) -> None:
        """版本号格式正确。"""
        assert isinstance(_VERSION, str)
        assert len(_VERSION) > 0
        assert "." in _VERSION

    def test_author_not_empty(self) -> None:
        assert isinstance(_AUTHOR, str)
        assert len(_AUTHOR) > 0

    def test_github_url(self) -> None:
        assert isinstance(_GITHUB_URL, str)
        assert _GITHUB_URL.startswith("https://")

    def test_license_not_empty(self) -> None:
        assert isinstance(_LICENSE, str)
        assert len(_LICENSE) > 0