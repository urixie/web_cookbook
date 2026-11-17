# 维护菜谱内容

上游为 [Anduin2017/HowToCook](https://github.com/Anduin2017/HowToCook)，使用 Unlicense。原始许可见 [LICENSE](../upstream/LICENSE)，作者和贡献者见 [上游提交记录](https://github.com/Anduin2017/HowToCook/graphs/contributors)。`upstream-lock.json` 记录完整 SHA、数量与每个文件的 SHA-256。外链配图保留在原文链接中，主站只将仓库内的原始素材作为本站配图，外链的独立授权由其发布者说明。

同步前先预览差异，再对同一 SHA 执行导入。可以加 `--source ../HowToCook` 复用本地 Git 检出。上游原文及素材直接按 Git 对象校验。本站的额外标注存放在 `metadata/overrides/`，同步保留该目录。

```powershell
python scripts/sync_upstream.py --sha <40位SHA> --preview
python scripts/sync_upstream.py --sha <40位SHA>
python scripts/validate_content.py
git status --short
git add upstream upstream-lock.json
git commit -m "chore: sync HowToCook content"
git push origin main
```

如需回滚，可在主站发布工作流选择此前菜谱仓库的完整提交 SHA，或者在菜谱仓库回退目标内容提交后推送。验证记录和锁定文件必须和内容一起回滚。

推送到 `main` 后先核对内容和路径。自动通知主站需在本仓库 **Settings → Secrets and variables → Actions → Repository secrets** 配置 `SITE_RELEASE_DISPATCH_TOKEN`。该细粒度令牌仅授权 `urixie/urixie.github.io` 的 **Actions: Read and write** 与 **Metadata: Read**。未配置时工作流只执行内容校验。首次导入由专门工作流执行，后续同步用上述本地命令。
