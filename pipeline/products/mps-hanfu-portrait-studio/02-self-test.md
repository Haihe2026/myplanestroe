# 汉服写真照相馆1.0.2 自测报告（A2）

2026-11-14T17:30:37+08:00。依据Muse固定任务4811e350a13c21922549d874ee941ad02066b189（仅压十图/logo，保功能，版本同步，成品≤3MB）。开发文档/选品单不变，按本轮现行两角色SOP由Codex开发验证；本报告不是A3结论。

**A2结论：通过。** 正式ZIP `mps-hanfu-portrait-studio-1.0.2.zip`，**2649840字节**，25文件，SHA256 `462837b50688cc5d9d6561e379637f99e5fbb0aa54d0f05aeb9ccb9edaa25b9d`。距离3,000,000B上限余350,160B。旧1.0.0/1.0.1 ZIP保留，1.0.1固定SHA c4d345920b0fd0c2f1d3443c2044f520876f21000865fcac3212a55314c2f6ea，超限旧包不交上传。

## 实际变更边界

十张PNG仍512×768 RGB、原裸名、数量/内容/构图及demos.json说明完全不变。RGB通道四步量化后PNG优化，每通道最大误差2，数值有损但独立原尺寸/脸部视觉无明显损失，最低PSNR46.3217dB；十图2,555,027B。logo只做无损PNG优化，512×512、418,249B，像素完全相等，SHA bf919e85511fe0ea2adbd8d43b1599314801357c5fcb7bec40445c9c6540bff5。

其余五文件仅版本metadata：SKILL.md frontmatter、_meta、studio/telemetry的SKILL_VERSION、first-turn-preview版本。SKILL正文、README、welcome_copy、场景/提示词、demos.json、随包测试及其他业务脚本原字节相同；逐文件差分和标准AST已核，业务逻辑未变。保PNG适配既有PNG-only加载器，无新增依赖/功能/资源调用。

## 自动化验证与环境

| 环境/命令（从02-package执行） | 实际结果 |
|---|---|
| Windows Python3.12.10：`python -X utf8 -I dev/offline_runner.py contract-native mps-hanfu-portrait-studio` | 64通过，0跳过；显式native fixture适配，非原样POSIX fixture全绿 |
| Windows：`python -X utf8 -I dev/offline_runner.py e2e dev/e2e_check.py mps-hanfu-portrait-studio dist/mps-hanfu-portrait-studio-1.0.2.zip` | 142通过，0跳过；进程内Mock，socket/urlopen禁止真实网络 |
| Ubuntu WSL2 Python3.12.3，Linux-native私有临时副本、`unshare -rn python3 -I dev/offline_runner.py contract mps-hanfu-portrait-studio` | 原样64通过，0跳过 |
| 同Linux隔离副本：`unshare -rn python3 -I dev/offline_runner.py e2e dev/e2e_check.py mps-hanfu-portrait-studio dist/mps-hanfu-portrait-studio-1.0.2.zip` | 142通过，0跳过 |
| 开发侧check_release_1_0_2.py | 实称重≤3MB、CRC、25文件、最多两级、十PNG、ZIP成员与源码逐字节一致，通过 |
| Python3.7标准语法AST | 随包py全部可解析；不是3.7解释器实际运行 |

完整结果、日志哈希和环境见 `02-package/dev/a2-result-1.0.2.json`；日志脱机器工作区前缀后保存在a2-evidence-1.0.2，原始日志本机保留。运行时只是标准库，开发解析依赖不进入包。

## Windows测试适配与诚实边界

初跑原样64有两条POSIX `/home/` fixture在Windows被解析到实际驱动器，预期硬写POSIX路径而失败；外部runner只把这两例中的四处合成根锚点转换为Windows实际驱动器，断言仍验证编码/还原/文件存在，没有改随包测试。原样142另有路径斜杠/编码预期和临时文件清理错误，原始失败日志保留；开发侧e2e只增加URL解码、双方统一斜杠、GC及有界测试目录清理保护。无删业务断言，也没有为测试放开认证/资格/计费/原任务锁。一次开发适配脚本缩进错误导致测试装置启动失败，修正后已重新验证，历史日志保留。

POSIX mode600只在Linux实测；**Windows ACL仍未验证**，不能以POSIX位推断。曾有未关闭测试句柄的ResourceWarning，非测试失败；若Windows32清理冲突保留fixture并记录，不吞测试体失败。派生检查从旧原字节假设改为“固定原来源SHA→当前压缩SHA”，旧生成provenance未伪造/覆盖。修改范围为开发测试装置，不在Skill ZIP内。

前序HNF01–04及PAY/E/FAM/TRV/MAT/SLV/离线demo/斜杠/欢迎句回归均由64契约和142端到端覆盖；最终A3还须按26项历史矩阵静态复核未回退，见后续03报告。

## 未验证及后续

新增真实上游/业务/支付/生产/上传均0；未调用真实客户账户。当前运行域名、认证与功能沿固定1.0.1，不借纯压缩任务修改。真实宿主/不@收藏/微信付款/平台上传未验证，附录D/D.6按长期豁免跳过。A2通过后提交固定package_ready，再对同一SHA做独立A3静态检查，交Muse由负责人手动上传。
