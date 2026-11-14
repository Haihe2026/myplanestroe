# 汉服写真照相馆1.0.2：A3静态自检通过

2026-11-14T17:44:26+08:00。已读WorkBuddy技能页记录见02-package/dev/official-read-1.0.2.json（2026-11-14 17:01:32+08:00，HTTP200；升级轮仍保留在线读取证据）。3MB限制来源为负责人上传实测和现行SOP，未冒称官方技能页列出此上限。

**结论：通过，开放包级阻断为空。** 固定package_ready提交 `2542db0a9dddf0f1e62a9777a6e39064738d0c92`；ZIP为`02-package/dist/mps-hanfu-portrait-studio-1.0.2.zip`，**2,649,840B**，25文件，SHA256 `462837b50688cc5d9d6561e379637f99e5fbb0aa54d0f05aeb9ccb9edaa25b9d`，Git blob `2ecb90c7a5b7c2d31ec3dbdebdb8b930fdfe09e0`。根A3认领时核对该固定提交和当前分支同一blob；独立审阅实际相同SHA干净包。后续ZIP若变更，本报告失效。

## 静态检查结果

- SHA/CRC/安全解包、无越界/符号链接、根/二级最多两级：通过。成品≤3,000,000B，留350,160B；不是把素材估算当成品验收。
- 原始YAML用独立PyYAML SafeLoader并拒重复键，八必填/合法类型、三对中英语义/画幅/像素逐项一致：通过。SKILL为15352B≤15360B；欢迎句逐字保持“欢迎使用WorkBuddy官方认证技能 汉服写真照相馆。”。
- 十PNG均RGB8、512×768、同裸名；独立分块CRC/zlib/扫描行及来源→派生SHA核验：通过。demos.json标题/数量/说明原字节同；十图2,555,027B。空格/#/%三个实际文件路径经独立CommonMark解析后仍定位：通过。
- logo外置PNG512×512、418249B，SHA bf919e85511fe0ea2adbd8d43b1599314801357c5fcb7bec40445c9c6540bff5；与固定旧logo逐像素相同：通过。十图颜色压缩非像素无损，原尺寸与脸部独立视觉无明显损失，详compression-visual-review.md；A3不重生或再改图。
- 原1.0.1到1.0.2共15成员变化：十图片＋五个版本metadata。SKILL只frontmatter version，studio/telemetry只版本常量，_meta和first-turn-preview只版本；其余十文件原字节同。业务脚本归一版本后AST相同，模板、文案、功能、清单、随包测试没有变化：通过。
- 已有账户/计费/同意/原任务锁/反馈和字节有界解码合同静态继承未回退；对客白标和禁用词规则没有新增泄漏。开发侧测试装置适配未进入ZIP。

## 前序缺陷逐项未回退

下表26个为派单具名/具名回归项；不为斜杠/欢迎句补造历史ID。TRV01/02续修及WED02/03另作为四个附加保护，详a3-recovery-review.json。HNF四项结合已通过1.0.1修复证据及实际源码/说明不变证明，不把静态复核冒充重新运行历史测试。

| 项 | 静态结论/依据 |
|---|---|
| HNF-A3-01 | 通过；1.0.1已关闭完整形制+outfit叠加/冲突消歧；studio.py仅SKILL_VERSION字面量改变，归一版本后AST同；README/refs/prompt/welcome原字节同。 |
| HNF-A3-02 | 通过；1.0.1已关闭strip_negated/route_intent修复；源码除版本常量逐字同，未退回硬拒否定词旧逻辑；SKILL只版本。 |
| HNF-A3-03 | 通过；SKILL53及119–120不自动重跑feedback，未知反馈仅显式同键同体补交；studio1306–1370和welcome与通过版原字节同；子审另核静态控制流。 |
| HNF-A3-04 | 通过；demos.json原字节同，侠客note仍为木质影棚/非实拍；图只颜色精度压缩，原来源/派生SHA及独立视觉通过。 |
| A3-PAY-01 | 通过；[{'source': 'studio', 'lines': [[238, 243], [699, 724], [1164, 1200]]}, {'source': 'welcome', 'lines': [[179, 189]]}, {'source': 'skill', 'lines': [[104, 107]]}] |
| A3-PAY-02 | 通过；[{'source': 'studio', 'lines': [[328, 339], [699, 724], [773, 801]]}, {'source': 'skill', 'lines': [[52, 52]]}] |
| A3-PAY-03 | 通过；[{'source': 'skill', 'lines': [[5, 5], [50, 54], [84, 84], [104, 106]]}] |
| A3-PAY-04 | 通过；[{'source': 'studio', 'lines': [[500, 510], [516, 568]]}] |
| A3-E01 | 通过；[{'source': 'skill', 'lines': [[8, 15]]}] |
| A3-E02 | 通过；[{'source': 'studio', 'lines': [[184, 191], [551, 568], [1055, 1058]]}, {'source': 'welcome', 'lines': [[202, 213]]}] |
| A3-E03 | 通过；[{'source': 'studio', 'lines': [[185, 191], [1055, 1058]]}, {'source': 'welcome', 'lines': [[202, 213]]}] |
| WED-A3-01 | 通过；[{'source': 'studio', 'lines': [[500, 501], [540, 568]]}] |
| A3-FAM-01 | 通过；[{'source': 'studio', 'lines': [[804, 817], [847, 855], [895, 916], [927, 986], [1062, 1100]]}] |
| A3-FAM-02 | 通过；[{'source': 'studio', 'lines': [[153, 155], [578, 584], [885, 916], [941, 961], [1062, 1100]]}, {'source': 'skill', 'lines': [[99, 99], [111, 114]]}] |
| A3-FAM-03 | 通过；[{'source': 'studio', 'lines': [[513, 537], [540, 568]]}] |
| TRV-01 | 通过；[{'source': 'studio', 'lines': [[727, 770], [831, 844]]}] |
| TRV-02 | 通过；[{'source': 'audit', 'lines': [[14, 17], [32, 91], [94, 131]]}, {'source': 'png', 'lines': [[142, 190], [261, 263]]}, {'source': 'jpeg', 'lines': [[112, 118], [158, 285], [288, 352]]}, {'source': 'studio', 'lines': [[1012, 1025]]}] |
| TRV-03 | 通过；[{'source': 'telemetry', 'lines': [[18, 38], [67, 79], [86, 123], [126, 158]]}] |
| TRV-04 | 通过；[{'source': 'studio', 'lines': [[367, 427]]}, {'source': 'skill', 'lines': [[30, 32], [88, 88], [96, 100]]}] |
| TRV-05 | 通过；[{'source': 'welcome', 'lines': [[40, 61], [196, 199]]}, {'source': 'skill', 'lines': [[98, 99]]}, {'source': 'studio', 'lines': [[650, 692], [807, 817]]}] |
| MAT-A3-01 | 通过；[{'source': 'skill', 'lines': [[1, 18]]}] |
| MAT-A3-02 | 通过；[{'source': 'studio', 'lines': [[680, 692], [804, 844], [1062, 1085]]}] |
| MAT-A3-03 | 通过；[{'source': 'skill', 'lines': [[96, 100]]}, {'source': 'studio', 'lines': [[594, 606]]}, {'source': 'welcome', 'lines': [[64, 82]]}] |
| SLV-A3-01 | 通过；[{'source': 'studio', 'lines': [[578, 625], [633, 661], [804, 810], [1062, 1066], [1088, 1100]]}, {'source': 'skill', 'lines': [[99, 99]]}] |
| slash-regression-no-independent-id | 通过；[{'source': 'studio', 'lines': [[176, 191], [565, 568], [1055, 1058]]}] |
| exact-welcome-no-independent-id | 通过；[{'source': 'welcome', 'lines': [[5, 7]]}, {'source': 'studio', 'lines': [[508, 510]]}, {'source': 'skill', 'lines': [[56, 56], [86, 86]]}] |

## A2证据复核与边界

仅只读复核A2报告/四条日志及其SHA：Windows64契约(native fixture adapter)+142 Mock、Linux原样64+142均OK、0跳过。原样Windows两项POSIX /home fixture失败及初期清理/路径问题保留；测试装置作原生锚点、解码、斜杠和清理适配，没有改ZIP或删业务断言。WindowsACL仍未验证，不能写成原样Windows套件无需适配或权限已验。完整命令、环境、失败留存和适配diff见02-self-test.md、dev/a2-result-1.0.2.json。

本A3没有导入/执行包、重跑A2、调用真实上游/业务、浏览器/真机、部署/重启或上传。D/D.6按长期豁免跳过；真实OAuth/付款/客户身份保持、生产运行字节和平台上传接受未验证。当前域名/功能按明确纯图片压缩任务沿1.0.1保持，未借通用规则另改生产。

1.0.0和1.0.1原ZIP保留追溯，超限旧包不交上传。本1.0.2达到test_passed条件，交Muse复核后由负责人手动上传同一固定ZIP及外置logo；codex_may_publish=false。
