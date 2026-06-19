# crawler パッケージの初期化ファイルです。
# クラウドワークス等の案件巡回クローラーを外部から扱いやすくします。

from .crowdworks_crawler import CrowdWorksCrawler

__all__ = ['CrowdWorksCrawler']
