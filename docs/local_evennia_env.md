# Local Evennia Env

## 目标

在本机 `C:\Users\CZH\Documents\Playground` 下准备一个可用于本地代码验证的 Evennia 运行环境，不依赖系统级安装。

## 当前结论

由于本机 `Python 3.14` 的 `venv/ensurepip` 链路存在权限异常，当前采用了“wheel 下载 + 本地解压”的方案：

- Evennia 本地环境目录：
  - `C:\Users\CZH\Documents\Playground\evennia-local-env`
- wheel 缓存目录：
  - `C:\Users\CZH\Documents\Playground\evennia-wheelhouse`
- 本地启动脚本：
  - `C:\Users\CZH\Documents\Playground\run-evennia-local.ps1`

## 当前安装内容

当前已安装：

- `evennia==6.0.0`
- Django / Twisted / DRF 及其依赖

构建方式：

- 先 `pip download` 到 `evennia-wheelhouse`
- 再直接将 `.whl` 解压到 `evennia-local-env`
- 所有内容都落在 `Playground` 目录下
- 不写入项目目录以外的位置

## 使用方式

### 1. 在 PowerShell 中加载本地环境

```powershell
. C:\Users\CZH\Documents\Playground\run-evennia-local.ps1
```

### 2. 做最小导入测试

```powershell
py -3.14 -c "import evennia"
py -3.14 -c "from importlib.metadata import version; print(version('evennia'))"
```

### 3. 带本地包目录执行项目脚本

```powershell
$env:PYTHONPATH='C:\Users\CZH\Documents\Playground\evennia-local-env'
py -3.14 some_script.py
```

## 为什么不直接用 venv

本机当前 `Python 3.14` 的 `ensurepip` 会在系统临时目录阶段报权限错误，导致：

- `python -m venv` 无法稳定创建带 pip 的完整环境

因此当前改用：

- `pip download -> wheel extract -> C:\Users\CZH\Documents\Playground\evennia-local-env`

这个方案的优点：

- 路径可控
- 便于迁移和清理
- 不依赖系统级 Python 环境修复

## 后续建议

如果后面需要更完整的本地集成测试环境，建议二选一：

1. 额外安装一个更稳定的 Python 版本，例如 `3.12/3.13`
2. 继续优先用 Docker 做贴近线上环境的集成测试

在当前机器条件下，这份本地包目录方案已经足够支持：

- 导入校验
- 模块级测试
- 序列化器 / 协议层 / 工具层验证
