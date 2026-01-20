# Project Structure Plugin

项目工程文件管理与目录结构规范化插件。

## 功能特性

- **项目初始化**: 使用标准化目录结构创建新项目
- **结构验证**: 检测违规文件并报告问题（ERROR/WARNING/INFO 分级）
- **根目录清理**: 自动将杂乱文件归类到正确子目录
- **多项目类型支持**: C/C++, ROS2, Python, Rust, Node.js, Embedded, Generic

## 核心原则

根目录只允许存放：
- 项目配置文件（CMakeLists.txt, package.json, Cargo.toml 等）
- 版本控制文件（.gitignore, .gitattributes）
- 项目文档（README.md, LICENSE）
- IDE 配置（.vscode/, .idea/）
- CI/CD 配置（.github/）

**其他一切文件必须归类到对应子目录**。

## 安装

```bash
/plugin install project-structure@jiusi-agent-plugins
```

## 使用

### 初始化新项目

```bash
# 格式: python3 init_project.py <project-name> --type <type> [--path <output-dir>]
python3 skills/project-structure/scripts/init_project.py myproject --type cpp
python3 skills/project-structure/scripts/init_project.py myros2pkg --type ros2
python3 skills/project-structure/scripts/init_project.py myapp --type python
```

支持的项目类型: `c`, `cpp`, `ros2`, `python`, `rust`, `nodejs`, `embedded`, `generic`

### 验证项目结构

```bash
# 格式: python3 validate_structure.py <project-path> [--fix] [--type <type>]
python3 skills/project-structure/scripts/validate_structure.py ./myproject
python3 skills/project-structure/scripts/validate_structure.py ./myproject --fix  # 自动修复
```

### 清理根目录

```bash
# 格式: python3 clean_root.py <project-path> [--dry-run] [--interactive]
python3 skills/project-structure/scripts/clean_root.py ./myproject --dry-run  # 预览
python3 skills/project-structure/scripts/clean_root.py ./myproject           # 执行
```

## 标准目录布局

```
project-root/
├── src/              # 源代码
├── include/          # 公共头文件 (C/C++)
├── lib/              # 第三方库
├── build/            # 构建输出 (gitignored)
├── docs/             # 文档
├── scripts/          # 构建/部署脚本
├── config/           # 配置文件
├── tests/            # 测试文件
├── assets/           # 静态资源
├── tools/            # 开发工具
└── examples/         # 示例代码
```

## License

MIT
