# 九思的 Claude Code 插件市场

Claude Code 插件集合，包含 OpenHarmony 移植工具、项目结构管理、邮件通知、知识库演进等工具。

## 安装 Marketplace

```bash
# 在 Claude Code 中执行
/plugin marketplace add Jiusi-pys/agent-plugins
```

## 可用插件

### ohos-porting

OpenHarmony/KaihongOS 软件移植工作流插件。

**功能特性：**
- 8 阶段移植工作流
- 6 个专用 Agent
- 11 个 Skill（含已有的 git-cicd-workflow, hdc-kaihongOS, ohos-cpp-style, ohos-cross-compile 等）
- 自动错误诊断 Hook
- 工作状态持久化

**安装：**
```bash
/plugin install ohos-porting@jiusi-agent-plugins
```

**使用：**
```bash
/ohos-porting:ohos-port-dev libcurl
```

---

### project-structure

项目工程文件管理与目录结构规范化插件。

**功能特性：**
- 项目初始化：使用标准化目录结构创建新项目
- 结构验证：检测违规文件并报告问题（ERROR/WARNING/INFO 分级）
- 根目录清理：自动将杂乱文件归类到正确子目录
- 多项目类型支持：C/C++, ROS2, Python, Rust, Node.js, Embedded, Generic

**核心原则：** 根目录只允许配置文件、文档、版本控制文件、CI/CD 配置。其他一切归类到子目录。

**安装：**
```bash
/plugin install project-structure@jiusi-agent-plugins
```

**使用：**
```bash
# 初始化新项目
python3 scripts/init_project.py myproject --type cpp

# 验证项目结构
python3 scripts/validate_structure.py ./myproject --fix

# 清理根目录
python3 scripts/clean_root.py ./myproject --dry-run
```

---

### email-notify

Gmail SMTP 邮件通知系统，任务完成时自动发送邮件提醒。

**功能特性：**
- Postfix + Gmail SMTP 中继配置
- Claude Code 任务完成自动通知
- 邮件开关控制

**安装：**
```bash
/plugin install email-notify@jiusi-agent-plugins
```

**使用：**
```bash
/email-notify:notify-config    # 配置邮件
/email-notify:notify-on        # 开启通知
/email-notify:notify-off       # 关闭通知
```

---

### skill-evolving-expert

知识库演进专家系统，自动积累问题解决方案。

**功能特性：**
- 问题-方案知识库管理
- 模式提取与索引
- 知识持久化与检索

**安装：**
```bash
/plugin install skill-evolving-expert@jiusi-agent-plugins
```

**使用：**
```bash
/skill-evolving-expert:kb-init    # 初始化知识库
```

## 目录结构

```
agent-plugins/
├── plugins/
│   ├── ohos-porting/           # OpenHarmony 移植工作流
│   ├── project-structure/      # 项目结构管理
│   ├── email-notify/           # 邮件通知
│   └── skill-evolving-expert/  # 知识库演进
└── README.md
```

## License

MIT
