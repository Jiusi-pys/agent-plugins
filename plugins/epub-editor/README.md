# EPUB 编排

编辑 EPUB 元数据、统计字数、修复目录定位、规范注释语义，并使用用户提供的图片替换封面。输出为新的 EPUB 文件，保留原文件。

本包导入自已安装的个人 `epub-editor` 插件，保留版本 `0.1.0+codex.20260917084344`、处理脚本及测试。该版本号包含原本的本地安装缓存标识。

## 安装与使用

从本仓库的 `jiusi-agent-plugins` Codex marketplace 安装 `epub-editor`，提供 EPUB 路径和修改要求，例如：“修改这本书的作者并统计字数，保留其他元数据。”

在工作目录的 Python 虚拟环境中安装依赖：

```sh
python -m venv .venv
# 激活虚拟环境后，在仓库根目录执行：
python -m pip install -r plugins/epub-editor/requirements.txt
```

也可直接使用命令行：

```sh
python plugins/epub-editor/scripts/epub_editor.py input.epub --inspect
python plugins/epub-editor/scripts/epub_editor.py input.epub output.epub --recount
python plugins/epub-editor/scripts/epub_editor.py input.epub output.epub --cover cover.png
```

元数据 JSON 字段见 [metadata.md](skills/epub-edit/references/metadata.md)，完整操作约定见 [SKILL.md](skills/epub-edit/SKILL.md)。封面仅接受用户提供的 JPEG/PNG；注释弹窗取决于阅读器支持。

退出码 `0` 表示结构处理完成，`2` 表示已生成输出但仍有待处理问题，`1` 表示失败。内部结构检查不等于通过 EPUBCheck。

## 验证

在仓库根目录执行：

```sh
python -m unittest discover -s plugins/epub-editor/tests -v
```

测试覆盖 EPUB 编排与元数据处理；运行前需安装 `requirements.txt` 中的依赖。
