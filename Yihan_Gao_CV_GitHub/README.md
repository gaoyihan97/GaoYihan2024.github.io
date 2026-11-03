# 高一涵 / Yihan Gao：个人主页与双语学术 CV

## 查看简历

- 个人主页：https://gaoyihan97.github.io/GaoYihan2024.github.io/
- 英文 CV：https://gaoyihan97.github.io/GaoYihan2024.github.io/cv/
- 中文 CV：https://gaoyihan97.github.io/GaoYihan2024.github.io/cv/zh.html
- 英文 PDF：`cv/Yihan_Gao_CV_EN.pdf`
- 中文 PDF：`cv/Yihan_Gao_CV_ZH.pdf`

## 以后如何更新

1. 打开仓库的 `data/cv.json`，点击铅笔编辑。
2. 修改对应内容。带 `en` 和 `zh` 的字段分别是英文和中文，论文的英文题目共用一份。
3. 修改最上面的 `updated` 日期，例如 `2026-11-03`。
4. 点击 **Commit changes**，保存到 `main`。
5. GitHub Actions 自动生成两种语言的网页和 PDF，再发布到同一个主页地址。一般需要几分钟，并非保存后立刻完成。

**首次启用一次即可：** 仓库 **Settings → Pages → Build and deployment → Source → GitHub Actions**。
然后打开 **Actions → Update bilingual CV and publish homepage → Run workflow**。

如果仓库限制 Actions，请先在 Settings → Actions 中允许使用 GitHub 官方 Actions。
工作流只需仓库自带的 `GITHUB_TOKEN`，不需要添加个人密钥。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `data/cv.json` | CV 的唯一资料来源，以后优先编辑这里 |
| `scripts/build_cv.py` | 生成双语网页和 PDF |
| `cv/` | 当前可直接使用的生成结果 |
| `index.html` | 原有个人主页，新增双语 CV 入口 |
| `.github/workflows/update-cv.yml` | GitHub 自动生成和部署设置 |
| `assets/fonts/` | 可再分发的开源字体及许可 |

工作流将最新结果直接部署到 GitHub Pages，并在每次运行中提供下载附件。
工作流不会把生成的 PDF 再提交回源代码仓库。因此，长期使用请下载网站上的 PDF，或下载对应 Actions 运行的附件。仓库 `cv/` 中的文件是首次制作时的版本，本地运行生成命令后可自行提交更新。

原有主页的其他文字暂时仍由 `index.html` 维护，不会因为修改 CV 数据而被覆盖。

## 本地生成

需要 Python 3.12 或更新版本：

```text
python -m pip install -r requirements.txt
python scripts/build_cv.py
```

生成用于 GitHub Pages 的完整目录：

```text
python scripts/build_cv.py --site-dir _site
```

`_site/` 只包含公开主页与双语 CV，不包含资料来源、参考 CV 或本地检查记录。

## 内容与维护约定

- 预计博士毕业时间：2027 年 8 月。
- 工作论文与已发表论文分别列出，SBCS 稿件仅写“已投稿”，不猜测审稿阶段。
- 会议报告与期刊论文分开。
- 教学经历仅记录已确认的助教身份；AAE3009 的习题课经历按用户提供的四个秋季学期列示。
- 其他课程的 `2024 S1` 等标记暂按原表述写作“2024, Semester 1”，未自行转换为学年。
- 中文课程名为便于理解的译名，英文版采用 PolyU 官方课程名称。
- 不公开电话，不添加未经确认的审稿经历、推荐人、技能水平或教学职责。
- 原则上先更新资料文件，再运行生成器，不直接修改 `cv/` 下的生成文件。

排版参考 Jian Liang 的公开 CV：衬线字体、蓝灰分节标题、右侧日期和论文编号。参考 PDF 不会上传到仓库。
