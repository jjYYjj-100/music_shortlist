# 音乐潜力候选筛选

运营在一周有 3 个试听名额。从当期第 21–35 名中，挑出下周可能进入前 20 名的歌曲。候选规则是已上榜、且上周名次减去本周名次为正。按升幅从大到小排序，同分时本周名次靠前的优先。基线使用同一个候选范围，按本周名次取前三。

需要 Python 3。使用标准库 SQLite。

```powershell
python shortlist.py recommend
python shortlist.py evaluate
python shortlist.py test
```

`get_shortlist(week, limit)` 是可接入大模型函数调用的入口。当前演示通过命令行直接调用这个函数。

当期只加载 2026 年 11 月 13 日榜单第 21–35 名。结果只在评测时读取下一期前 20 名。榜单的 LW 字段提供与上一期名次的对应关系，因此可以用它回查命中。榜单是英国市场的综合排名，观察指标是进入前 20 名。回看这一期前已见到榜单结果，因此这一期只能作为回测样例。季节性歌曲入选也提示了规则可能受节日影响，需要另找未看过的周检验。

- [选歌周源数据](https://www.officialcharts.com/charts/singles-chart/20261113/7501/)
- [结果周源数据](https://www.officialcharts.com/charts/singles-chart/20261120/7501/)
