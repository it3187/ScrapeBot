# evaluator パッケージの初期化ファイルです。
# Gemini APIベースの案件適合度判定エンジンを外部から扱いやすくします。

from .job_evaluator import JobEvaluator

__all__ = ['JobEvaluator']
