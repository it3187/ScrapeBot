# scraper パッケージの初期化ファイルです。
# 外部からスクレイパーをインポートしやすいように整理します。

from .base_scraper import BaseScraper
from .iosis_scraper import IosisScraper
from .janpara_scraper import JanparaScraper
from .yahoo_shopping_scraper import YahooShoppingScraper

# 外部に公開する主要クラスを明示的に指定します。
__all__ = ['BaseScraper', 'IosisScraper', 'JanparaScraper', 'YahooShoppingScraper']
