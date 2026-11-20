# 维护菜谱内容

上游为 [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook)，使用 Unlicense。原始许可见 [LICENSE](../upstream/LICENSE)，作者和贡献者见 [上游提交记录](https://github.com/Anduin2017/HowToCook/graphs/contributors)。`upstream-lock.json` 记录完整 SHA、数量与每个文件的 SHA-256。外链配图保留在原文链接中，主站只将仓库内的原始素材作为本站配图，外链的独立授权由其发布者说明。

同步前先预览差异，再对同一 SHA 执行导入。可以加 `--source ../HowToCook` 复用本地 Git 检出。上游原文及素材直接按 Git 对象校验。本站的额外标注存放在 `metadata/overrides/`，同步保留该目录。未引用的上游成品图可通过 `metadata/overrides/covers.json` 复用；新生成的独立封面放在 `metadata/covers/<分类>/`，并按菜谱 Markdown 相对路径登记。不要改动 `upstream/` 或 `upstream-lock.json`。

```powershell
python scripts/sync_upstream.py --sha <40位SHA> --preview
python scripts/sync_upstream.py --sha <40位SHA>
python scripts/validate_content.py
git status --short
git add upstream upstream-lock.json
git commit -m "chore: sync HowToCook content"
git push origin main
```

推送到 `main` 后，在主站仓库运行 `python scripts/release_local.py --webkit --publish`，验证并上线。回滚菜谱内容时将目标内容和对应的锁定文件一并还原、验证和提交，再重新发布主站。完整步骤见 [主站维护说明](https://github.com/urixie/urixie.github.io/blob/main/docs/repository-split.md)。
